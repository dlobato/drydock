"""AVD owns catalog generation and execution. Drydock enforces required coverage."""

from collections import Counter
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from .core import UserError, NODES, save

ROOT = Path(__file__).resolve().parents[1]
PLAYBOOK = ROOT / 'playbooks/anta.yml'


def invoke(directory, hosts, structured_dir, dry_run, timeout):
    directory = Path(directory).resolve()
    inventory = {'all': {'vars': {'ansible_connection': 'local',
        'ansible_python_interpreter': sys.executable}, 'children': {'FABRIC': {'hosts': {
            host['name']: {'ansible_host': host['host'], 'anta_port': host['port']} for host in hosts}}}}}
    save(directory / 'inventory.json', inventory)
    variables = {'root_dir': str(directory), 'structured_dir': str(structured_dir),
                 'anta_runner_dry_run': dry_run}
    save(directory / 'variables.json', variables)
    report = directory / 'anta/reports/anta_report.json'
    report.unlink(missing_ok=True)
    environment = {**os.environ, 'ANSIBLE_CONFIG': str(ROOT / 'ansible.cfg'),
        'ANSIBLE_COLLECTIONS_PATH': str(ROOT / '.collections'), 'ANSIBLE_LOCAL_TEMP': str(ROOT / '.ansible/tmp'),
        'ANSIBLE_LOG_PATH': '/dev/null', 'ANSIBLE_NOCOLOR': '1'}
    process = subprocess.Popen([str(Path(sys.executable).with_name('ansible-playbook')),
        str(PLAYBOOK), '-i', str(directory / 'inventory.json'), '-e', '@' + str(directory / 'variables.json')],
        cwd=ROOT, env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    try:
        process.wait(timeout=timeout)
    finally:
        if process.poll() is None:
            # Stop Ansible and its worker processes before removing tunnels or temporary inputs.
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
    rows = json.loads(report.read_text()) if report.exists() else []
    return process.returncode, rows


def coverage(directory, bundle):
    from anta.catalog import AntaCatalog

    expected = Counter()
    for name in sorted(NODES):
        catalog = AntaCatalog.parse(Path(directory) / 'anta/avd_catalogs' / f'{name}.json', file_format='json')
        tests = {item.test.__name__: item for item in catalog.tests}
        required = {'VerifyBGPPeerSession', 'VerifyInterfacesStatus', 'VerifyLLDPNeighbors', 'VerifyReachability'}
        if name.startswith('leaf'):
            required |= {'VerifyMlagStatus', 'VerifyMlagConfigSanity', 'VerifyVxlanConfigSanity',
                         'VerifyIPv4RoutePresencePerVRF', 'VerifyPortChannels'}
        if not required <= tests.keys():
            raise UserError(f'AVD catalog lacks required coverage for {name}.')
        interfaces = tests['VerifyInterfacesStatus'].inputs.model_dump(mode='json')['interfaces']
        active = {item['name'] for item in interfaces if item['status'] == 'up'}
        if not set(bundle.interfaces[name]) <= active or (name.startswith('leaf') and 'Vxlan1' not in active):
            raise UserError(f'AVD catalog excludes required switch interfaces for {name}.')
        for item in catalog.tests:
            description = item.inputs.result_overwrite.description or item.test.description
            expected[(name, item.test.__name__, description)] += 1
    return expected


def prepare(bundle, private, directory):
    structured = Path(private) / 'structured_configs'
    structured.mkdir(mode=0o700)
    for name in sorted(NODES):
        (structured / f'{name}.yml').write_text(bundle.files[f'intended/structured_configs/{name}.yml'])
    hosts = [{'name': name, 'host': '127.0.0.1', 'port': 10000 + index} for index, name in enumerate(sorted(NODES))]
    code, rows = invoke(directory, hosts, structured, True, 120)
    if code:
        raise UserError('AVD anta_runner failed to generate the required catalogs.')
    expected = coverage(directory, bundle)
    save(Path(directory) / 'expected.json', [{'name': name, 'test': test, 'description': description, 'count': count}
                                            for (name, test, description), count in sorted(expected.items())])
    return structured, expected


def converge(hosts, structured, directory, expected, timeout, results):
    from .flow import acceptance

    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('ANTA convergence timed out.')
        code, rows = invoke(directory, hosts, structured, False, remaining)
        if rows:
            results[:] = rows
        outcome = acceptance(results, expected)
        if not code and outcome['passed']:
            return outcome
        time.sleep(min(10, max(0, deadline - time.monotonic())))

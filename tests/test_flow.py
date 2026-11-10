"""Offline contract tests. No provider calls or device images."""

from contextlib import contextmanager
from dataclasses import asdict
import io
import json
from pathlib import Path
import signal
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

import yaml

from drydock import cloud, flow
from drydock.core import Bundle, ENV_LABEL, LAB_LABEL, Environment, NODES, readiness


IMAGE = 'europe-west1-docker.pkg.dev/demo-project/images/ceos@sha256:' + 'a' * 64
ENV = Environment('demo-project', 'europe-west1-b', 'drydock-demo', '1.36.4-gke.2046003', '0.11.0', IMAGE)
IDENTITY = {'repository': 'example/repo', 'commit': 'abc123', 'run': 'local-demo', 'attempt': '1'}
LAB = 'lab-123456789abc'


def bundle_files():
    nodes = {name: {'mgmt-ipv4': f"192.0.2.{20 + int(name[-1]) if name.startswith('leaf') else 10 + int(name[-1])}",
                    'startup-config': f'intended/configs/{name}.cfg'} for name in sorted(NODES)}
    links = [{'endpoints': [f'leaf{leaf}:eth{spine}', f'spine{spine}:eth{leaf}']}
             for leaf in range(1, 5) for spine in (1, 2)]
    links += [{'endpoints': [f'leaf{leaf}:eth{port}', f'leaf{leaf+1}:eth{port}']}
              for leaf in (1, 3) for port in (6, 7)]
    topology = {'name': 'FABRIC', 'prefix': '', 'mgmt': {'network': 'custom_mgmt', 'ipv4-subnet': '192.0.2.0/24'},
                'topology': {'defaults': {'kind': 'arista_ceos'}, 'kinds': {'arista_ceos': {
                    'image': IMAGE, 'enforce-startup-config': True,
                    'binds': ['interface_mapping.json:/mnt/flash/EosIntfMapping.json:ro']}},
                    'nodes': nodes, 'links': links}}
    from pyavd import get_device_config
    structured = {name: {"hostname": name, "management_api_http": {"enable_https": True}} for name in NODES}
    return {'FABRIC-topology.clab.yml': yaml.safe_dump(topology), 'interface_mapping.json': json.dumps({
        'ManagementIntf': {'eth0': 'Management1'},
        'EthernetIntf': {f'eth{p}': f'Ethernet{p}' for p in (1, 2, 3, 4, 6, 7)}}),
        **{f'intended/configs/{name}.cfg': get_device_config(structured[name]) for name in NODES},
        **{f'intended/structured_configs/{name}.yml': yaml.safe_dump(structured[name]) for name in NODES}}


def make_bundle(directory, mutate=None):
    files = bundle_files()
    if mutate:
        mutate(files)
    path = Path(directory) / 'bundle.tar'
    with tarfile.open(path, 'w') as archive:
        for name, text in files.items():
            entry = tarfile.TarInfo(name)
            entry.size = len(text.encode())
            archive.addfile(entry, io.BytesIO(text.encode()))
    return Bundle.load(path)


class FakeEnvironment:
    """Persist ownership like Kubernetes, including optimistic update conflicts."""
    def __init__(self):
        self.name, self.namespace = ENV.name, ENV.namespace
        self.project, self.zone = ENV.project, ENV.zone
        self.cluster_version, self.clabernetes_version = ENV.cluster_version, ENV.clabernetes_version
        self.records, self.namespaces, self.worker_pools, self.applied, self.calls = {}, [], [], [], []
        self.fail_pool, self.fail_delete = False, False

    def objects(self, kind, namespace=None, labels=None):
        if kind == 'configmaps':
            return [json.loads(json.dumps(obj)) for lab, obj in self.records.items() if not labels or
                    LAB_LABEL + '=' not in labels or lab in labels]
        if kind == 'namespaces':
            return json.loads(json.dumps(self.namespaces))
        return []

    def kube(self, *args, data=None):
        self.calls.append(('kube', args))
        if args[0] in ('create', 'replace'):
            obj = json.loads(data)
            if obj['kind'] == 'ConfigMap':
                name = obj['metadata']['name']
                old = self.records.get(name)
                if args[0] == 'create' and old:
                    raise RuntimeError('Conflict')
                if args[0] == 'replace' and (not old or obj['metadata']['resourceVersion'] != old['metadata']['resourceVersion']):
                    raise RuntimeError('Conflict')
                obj['metadata']['resourceVersion'] = str(int(old['metadata']['resourceVersion']) + 1 if old else 1)
                self.records[name] = obj
            elif obj['kind'] == 'Namespace':
                self.namespaces.append(obj)
        elif args[0] == 'delete':
            if self.fail_delete:
                raise RuntimeError('namespace deletion failed')
            self.namespaces = [n for n in self.namespaces if n['metadata']['name'] != args[2]]
        return '{}'

    def gcloud(self, *args):
        self.calls.append(('gcloud', args))
        if args[:3] == ('container', 'node-pools', 'list'):
            return json.dumps(self.worker_pools)
        if args[:3] == ('container', 'node-pools', 'create'):
            self.assert_record_before_pool(args[3])
            self.worker_pools.append({'name': args[3], 'config': {'labels': cloud.pool_labels(self, args[3])}})
            if self.fail_pool:
                raise RuntimeError('allocation interrupted after provider accepted it')
        if args[:3] == ('container', 'node-pools', 'delete'):
            if self.fail_delete:
                raise RuntimeError('provider deletion failed')
            self.worker_pools = [p for p in self.worker_pools if p['name'] != args[3]]
        if args[:2] == ('auth', 'print-access-token'):
            return 'secret-token'
        return '{}'

    def assert_record_before_pool(self, lab):
        assert lab in self.records

    def apply(self, obj):
        self.applied.append(obj)


class BundleTests(unittest.TestCase):
    def test_valid_bundle_preserves_identities(self):
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory)
        self.assertEqual(set(bundle.interfaces), NODES)

    def test_reject_unsafe_missing_and_unsupported_inputs(self):
        changes = [lambda f: f.pop('intended/configs/leaf4.cfg'),
                   lambda f: f.update({'../outside': 'x'}),
                   lambda f: f.update({'FABRIC-topology.clab.yml': f['FABRIC-topology.clab.yml'].replace('arista_ceos', 'linux')}),
                   lambda f: f.update({'FABRIC-topology.clab.yml': f['FABRIC-topology.clab.yml'].replace(IMAGE, 'ceos:latest')}),
                   lambda f: f.update({'intended/configs/leaf1.cfg': 'hostname wrong\n'})]
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
                make_bundle(directory, change)

    def test_duplicate_and_symlink_rejected(self):
        for kind in ('duplicate', 'symlink'):
            with tempfile.TemporaryDirectory() as directory:
                make_bundle(directory)
                path = Path(directory) / 'bundle.tar'
                with tarfile.open(path, 'a') as archive:
                    member = tarfile.TarInfo('interface_mapping.json' if kind == 'duplicate' else 'link')
                    if kind == 'symlink':
                        member.type = tarfile.SYMTYPE
                        member.linkname = '/etc/passwd'
                    archive.addfile(member)
                with self.assertRaises(ValueError):
                    Bundle.load(path)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.bundle = make_bundle(self.temp.name)
        self.env = FakeEnvironment()

    def test_validation_precedes_allocation(self):
        for lifetime in (0, 241, True):
            with self.assertRaises(ValueError):
                cloud.create_lab(self.env, self.bundle, IDENTITY, lifetime)
        with self.assertRaises(ValueError):
            cloud.create_lab(self.env, self.bundle, {**IDENTITY, 'attempt': ''})
        self.assertFalse(self.env.calls)

    def test_distinct_attempts_and_private_switches(self):
        first = cloud.create_lab(self.env, self.bundle, IDENTITY)
        second = cloud.create_lab(self.env, self.bundle, {**IDENTITY, 'attempt': '2'})
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(first['provenance']['commit'], second['provenance']['commit'])
        topologies = [o for o in self.env.applied if o['kind'] == 'Topology']
        for obj in topologies:
            self.assertEqual(obj['spec']['expose'], {'exposeType': 'ClusterIP', 'disableAutoExpose': True})
            definition = yaml.safe_load(obj['spec']['definition']['containerlab'])
            self.assertEqual(set(definition['topology']['nodes']), NODES)
            self.assertTrue(all(n['kind'] == 'arista_ceos' for n in definition['topology']['nodes'].values()))
        self.assertNotEqual(topologies[0]['metadata']['namespace'], topologies[1]['metadata']['namespace'])
        deleted = cloud.delete_lab(self.env, first['id'])
        self.assertTrue(deleted['deleted'])
        self.assertEqual([p['name'] for p in self.env.worker_pools], [second['id']])
        self.assertTrue(cloud.delete_lab(self.env, first['id'])['deleted'])

    def test_partial_allocation_discovered_and_retried(self):
        self.env.fail_pool = True
        with self.assertRaises(RuntimeError):
            cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        self.assertEqual(cloud.lab_record(self.env, LAB)['state'], 'creating')
        self.env.fail_delete = True
        with patch('drydock.cloud.now', return_value=10**12):
            failed = cloud.reap(self.env)
            self.assertFalse(failed[0]['deleted'])
            self.assertTrue(cloud.lab_record(self.env, LAB)['overdue'])
            self.env.fail_delete = False
            self.assertTrue(cloud.reap(self.env)[0]['deleted'])
            # A late provider allocation is still removed after the record says deleted.
            self.env.worker_pools.append({'name': LAB, 'config': {'labels': cloud.pool_labels(self.env, LAB)}})
            self.assertTrue(cloud.reap(self.env)[0]['deleted'])
        self.assertFalse(self.env.worker_pools)

    def test_refuse_foreign_namespace_and_pool(self):
        for foreign in ('namespace', 'pool'):
            with self.subTest(foreign=foreign):
                env = FakeEnvironment()
                cloud.create_lab(env, self.bundle, IDENTITY, lab=LAB)
                if foreign == 'namespace':
                    env.namespaces[0]['metadata']['labels'] = {ENV_LABEL: 'another', 'unrelated': 'label'}
                else:
                    env.worker_pools[0]['config']['labels'] = {'unrelated': 'label'}
                with self.assertRaises(ValueError):
                    cloud.delete_lab(env, LAB)
                self.assertTrue(env.worker_pools)

    def test_stale_update_cannot_undo_cleanup(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        stale = cloud.lab_record(self.env, LAB)
        cloud.delete_lab(self.env, LAB)
        with self.assertRaises(RuntimeError):
            cloud.write_record(self.env, {**stale, 'state': 'running'})
        self.assertEqual(cloud.lab_record(self.env, LAB)['state'], 'deleted')

    def test_cleaner_refreshes_token_and_has_independent_cadence(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        before = len(self.env.applied)
        self.assertEqual(cloud.reap(self.env), [])
        self.assertEqual(self.env.applied[before]['kind'], 'Secret')
        cron = next(o for o in cloud.cleaner_objects(ENV) if o['kind'] == 'CronJob')
        self.assertEqual(cron['spec']['schedule'], '*/5 * * * *')
        self.assertEqual(cron['spec']['concurrencyPolicy'], 'Forbid')
        self.assertIn(ENV.cleanup_image, str(cron))

    def test_pending_allocation_prevents_false_deletion_success(self):
        cloud.create_lab(self.env, self.bundle, IDENTITY, lab=LAB)
        original = self.env.gcloud
        def gcloud(*args):
            if args[:3] == ('container', 'operations', 'list'):
                return json.dumps([{'name': 'pending-create', 'status': 'RUNNING',
                    'targetLink': f'projects/p/zones/z/clusters/{ENV.name}/nodePools/{LAB}'}])
            return original(*args)
        with patch.object(self.env, 'gcloud', side_effect=gcloud):
            result = cloud.delete_lab(self.env, LAB)
        self.assertFalse(result['deleted'])
        self.assertEqual(result['pending_operations'], ['pending-create'])


class AcceptanceTests(unittest.TestCase):
    def test_missing_skipped_error_and_duplicate_cannot_pass(self):
        expected = {('leaf1', 'VerifyMlagStatus', '')}
        for statuses in ([], ['skipped'], ['error'], ['failure'], ['success', 'skipped'], ['success', 'success']):
            results = [{'name': 'leaf1', 'test': 'VerifyMlagStatus', 'result': status} for status in statuses]
            self.assertFalse(flow.acceptance(results, expected)['passed'])
        self.assertTrue(flow.acceptance([{'name': 'leaf1', 'test': 'VerifyMlagStatus', 'result': 'success'}], expected)['passed'])

    def test_junit_contains_missing_required_results(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as directory:
            outcome = flow.reports(Path(directory), [], {('leaf1', 'VerifyMlagStatus', '')})
            root = ET.parse(Path(directory) / 'anta.xml').getroot()
            self.assertEqual(root.attrib['failures'], '1')
            self.assertEqual(root.find('testcase/failure').attrib['message'], 'missing')
            self.assertFalse(outcome['passed'])

    def test_probe_rejects_wrong_identity(self):
        with patch('drydock.flow.eapi', return_value=[{'hostname': 'other'}, {'version': 'test'}]):
            with self.assertRaises(ValueError):
                flow.probe([{'name': 'leaf1', 'port': 12345}], 'secret')
        with patch('drydock.flow.probe', side_effect=OSError):
            self.assertIsNone(flow.available_probe([], 'secret'))

    def test_empty_and_stale_readiness_fail(self):
        self.assertTrue(readiness([]))
        self.assertIn('topology is not current and ready', readiness([{'kind': 'Topology',
            'metadata': {'generation': 2}, 'status': {'observedGeneration': 1, 'topologyReady': True, 'topologyState': 'running'}}]))

    def test_status_probes_api_and_preserves_switch_identities(self):
        with patch('drydock.flow.snapshot', return_value=({}, [], [])), \
             patch('drydock.flow.tunnels', side_effect=fake_tunnels), \
             patch('drydock.flow.probe', side_effect=OSError):
            result = flow.status(ENV, LAB, 'secret')
        self.assertFalse(result['ready'])
        self.assertEqual({host['name'] for host in result['inventory']}, NODES)

    def test_one_reachability_result_cannot_replace_another(self):
        from collections import Counter
        expected = Counter({('leaf1', 'VerifyReachability', 'underlay'): 1,
                            ('leaf1', 'VerifyReachability', 'peers'): 1})
        rows = [{'name': 'leaf1', 'test': 'VerifyReachability', 'description': 'underlay', 'result': 'success'}] * 2
        self.assertFalse(flow.acceptance(rows, expected)['passed'])


@contextmanager
def fake_tunnels(env, lab):
    yield [{'name': n, 'port': 12345, 'host': '127.0.0.1', 'tags': [n]} for n in sorted(NODES)]


class FlowTests(unittest.TestCase):
    def run_flow(self, failure=None, cleanup_success=True):
        with tempfile.TemporaryDirectory() as directory:
            bundle = make_bundle(directory)
            expected = {(name, "GeneratedTest", "") for name in NODES}

            def converge(hosts, structured, output, required, timeout, results):
                results.extend({'name': name, 'test': test, 'result': 'failure' if failure == 'anta' else 'success'}
                               for name, test, description in sorted(required))
                if failure == 'timeout':
                    raise TimeoutError('timeout')
                if failure == 'cancel':
                    raise flow.Canceled('cancel')
                return flow.acceptance(results, required)

            with patch('drydock.flow.prepare', return_value=(Path(directory), expected)), \
                 patch('drydock.flow.create_lab', side_effect=RuntimeError if failure == 'allocation' else None), \
                 patch('drydock.flow.snapshot', return_value=({}, [], [])), \
                 patch('drydock.flow.tunnels', side_effect=RuntimeError if failure == 'tunnel' else fake_tunnels), \
                 patch('drydock.flow.probe', return_value={n: 'test' for n in NODES}), \
                 patch('drydock.flow.converge', side_effect=converge), \
                 patch('drydock.flow.network_diagnostics', return_value={}), \
                 patch('drydock.flow.diagnostics', return_value={}), \
                 patch('drydock.flow.reports', side_effect=OSError if failure == 'report' else flow.reports), \
                 patch('drydock.flow.cleanup', return_value={'deleted': cleanup_success}) as cleanup:
                result = flow.test_flow(ENV, bundle, IDENTITY, 'TOP-SECRET', directory)
                cleanup.assert_called_once()
                report_text = ''.join(p.read_text() for p in (Path(directory) / result['lab']).iterdir())
                self.assertNotIn('TOP-SECRET', report_text)
                self.assertNotIn('secret-token', report_text)
                self.assertEqual(result['provenance'], IDENTITY)
                return result

    def test_success_requires_tests_and_cleanup(self):
        self.assertTrue(self.run_flow()['passed'])
        self.assertFalse(self.run_flow(cleanup_success=False)['passed'])
        outcome = self.run_flow('anta', cleanup_success=False)
        self.assertFalse(outcome['tests']['passed'])
        self.assertFalse(outcome['cleanup']['deleted'])

    def test_failure_paths_always_cleanup(self):
        for failure in ('allocation', 'tunnel', 'anta', 'report', 'timeout', 'cancel'):
            with self.subTest(failure=failure):
                self.assertFalse(self.run_flow(failure)['passed'])

    def test_invalid_deadlines_do_not_allocate(self):
        with tempfile.TemporaryDirectory() as directory, patch('drydock.flow.create_lab') as create:
            bundle = make_bundle(directory)
            with self.assertRaises(ValueError):
                flow.test_flow(ENV, bundle, IDENTITY, 'secret', directory, lifetime=1)
            create.assert_not_called()

    def test_sigterm_uses_cancellation_path(self):
        previous = signal.getsignal(signal.SIGTERM)
        with self.assertRaises(flow.Canceled), flow.cancellation():
            signal.raise_signal(signal.SIGTERM)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_partial_tunnel_start_stops_children(self):
        process = Mock()
        process.poll.return_value = None
        with patch('drydock.flow.subprocess.Popen', side_effect=[process, OSError]), \
             patch('drydock.flow.wait_for', return_value=12345):
            with self.assertRaises(OSError):
                with flow.tunnels(ENV, LAB):
                    pass
        process.terminate.assert_called_once()
        process.wait.assert_called_once()


if __name__ == '__main__':
    unittest.main()

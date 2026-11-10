"""Run the actual AVD role offline and require complete switch coverage."""

from collections import Counter
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import Mock, patch

from drydock import anta, flow
from test_flow import make_bundle, IMAGE


class AntaRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.directory = Path(cls.temp.name)
        source = Path('artifacts/example/containerlab/bundle.tar')
        if not source.exists():
            raise RuntimeError('Run make example-bundle-test before make test.')
        with tarfile.open(source) as archive:
            files = {m.name: archive.extractfile(m).read().decode() for m in archive}
        import yaml
        topology = yaml.safe_load(files['FABRIC-topology.clab.yml'])
        topology['topology']['kinds']['arista_ceos']['image'] = IMAGE
        files['FABRIC-topology.clab.yml'] = yaml.safe_dump(topology)
        cls.bundle = make_bundle(cls.directory, lambda data: data.update(files))
        cls.structured, cls.expected = anta.prepare(cls.bundle, cls.directory, cls.directory / 'preview')

    def test_actual_role_generates_complete_catalog_and_omits_unused_endpoints(self):
        self.assertEqual(sum(self.expected.values()), 54)
        for name in ('leaf1', 'leaf2', 'leaf3', 'leaf4'):
            self.assertTrue(any(k[:2] == (name, 'VerifyMlagStatus') for k in self.expected))
            self.assertTrue(any(k[:2] == (name, 'VerifyVxlanConfigSanity') for k in self.expected))
            catalog = json.loads((self.directory / f'preview/anta/avd_catalogs/{name}.json').read_text())
            interfaces = next(t['VerifyInterfacesStatus']['interfaces'] for t in catalog['anta.tests.interfaces']
                              if 'VerifyInterfacesStatus' in t)
            active = {i['name'] for i in interfaces}
            self.assertTrue({'Ethernet1', 'Ethernet2', 'Ethernet6', 'Ethernet7', 'Vxlan1'} <= active)
            self.assertFalse({'Ethernet4', 'Ethernet5', 'Port-Channel4', 'Port-Channel5'} & active)
        rows = json.loads((self.directory / 'preview/anta/reports/anta_report.json').read_text())
        self.assertEqual(Counter((r['name'], r['test'], r.get('description', '')) for r in rows), self.expected)
        self.assertFalse(flow.acceptance(rows, self.expected)['passed'])  # dry-run never passes acceptance

    def test_missing_mlag_generation_fails_coverage(self):
        with tempfile.TemporaryDirectory() as directory:
            shutil.copytree(self.directory / 'preview/anta', Path(directory) / 'anta')
            path = Path(directory) / 'anta/avd_catalogs/leaf4.json'
            catalog = json.loads(path.read_text())
            del catalog['anta.tests.mlag']
            path.write_text(json.dumps(catalog))
            with self.assertRaises(ValueError):
                anta.coverage(directory, self.bundle)

    def test_convergence_keeps_failures_and_requires_role_success(self):
        rows = [{'name': n, 'test': t, 'description': description, 'result': 'success'}
                for (n, t, description), count in self.expected.items() for _ in range(count)]
        results = []
        with patch('drydock.anta.invoke', side_effect=[(2, rows), (0, rows)]) as invoke, \
             patch('drydock.anta.time.sleep'):
            self.assertTrue(anta.converge([], self.structured, self.directory, self.expected, 10, results)['passed'])
            self.assertEqual(invoke.call_count, 2)
        with patch('drydock.anta.invoke', side_effect=TimeoutError), self.assertRaises(TimeoutError):
            anta.converge([], self.structured, self.directory, self.expected, 10, results)
        self.assertEqual(len(results), 54)

    def test_timeout_stops_ansible_process_group(self):
        process = Mock(pid=123456, returncode=None)
        process.wait.side_effect = [subprocess.TimeoutExpired('ansible-playbook', 1), None]
        process.poll.return_value = None
        with tempfile.TemporaryDirectory() as directory, patch('drydock.anta.subprocess.Popen', return_value=process), \
             patch('drydock.anta.os.killpg') as kill:
            with self.assertRaises(subprocess.TimeoutExpired):
                anta.invoke(directory, [], self.structured, False, 1)
        kill.assert_called_once()


if __name__ == '__main__':
    unittest.main()

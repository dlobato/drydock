"""Exercise CLI results through a Kubernetes-only test boundary."""

from contextlib import redirect_stdout
from dataclasses import asdict
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import yaml

from drydock import __main__ as cli
from drydock.core import Environment, NODES
from test_lifecycle import ENV, IDENTITY, FakeEnvironment, make_bundle, switch_pods


def ready_items():
    items = [{'kind': 'Topology', 'metadata': {'name': 'fabric', 'generation': 1},
              'status': {'observedGeneration': 1, 'topologyReady': True, 'topologyState': 'running'}}]
    for name in sorted(NODES):
        items.append({'kind': 'Node', 'metadata': {'name': name, 'generation': 1},
                      'status': {'readiness': 'ready', 'planDigest': 'digest', 'conditions': [
                          {'type': kind, 'status': 'True', 'observedGeneration': 1}
                          for kind in ('PlanApplied', 'Prepared', 'ConnectivityReady', 'ContainersReady')]}})
        items.append({'kind': 'Service', 'metadata': {'name': name},
                      'spec': {'type': 'ClusterIP', 'ports': [{'port': 443}]}})
    items.extend({'kind': 'Link', 'status': {'conditions': [{'type': 'Accepted', 'status': 'True'}]}}
                 for _ in range(12))
    for pod in switch_pods():
        pod['status']['conditions'] = [{'type': 'Ready', 'status': 'True'}]
        items.append(pod)
    return items


class LifecycleCliTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.backend = FakeEnvironment()
        self.environment = self.directory / 'environment.yml'
        self.environment.write_text(yaml.safe_dump(asdict(ENV)))
        make_bundle(self.directory)
        self.create_args = ['lab', 'create', str(self.directory / 'bundle.tar')]
        for key, value in IDENTITY.items():
            self.create_args.extend(['--' + key, value])
        runner = patch('drydock.core.run', side_effect=self.kubectl)
        runner.start()
        self.addCleanup(runner.stop)
        # The CLI sets a restrictive process umask for files that contain private input.
        previous = os.umask(0o077)
        self.addCleanup(os.umask, previous)

    def kubectl(self, command, *, data=None):
        prefix = ENV.kube_command()
        self.assertEqual(command[:len(prefix)], prefix)
        args = command[len(prefix):]
        if args[0] == 'get':
            namespace = args[args.index('-n') + 1] if '-n' in args else None
            labels = args[args.index('-l') + 1] if '-l' in args else None
            items = self.backend.objects(args[1], namespace, labels)
            if args[1].startswith('topologies.'):
                items = ready_items()
            return json.dumps({'items': items})
        if args[0] == 'apply':
            self.backend.apply(json.loads(data))
            return '{}'
        return self.backend.kube(*args, data=data)

    def invoke(self, *args):
        output = io.StringIO()
        with redirect_stdout(output):
            code = cli.main(['--environment', str(self.environment), *args])
        return code, json.loads(output.getvalue())

    def test_create_authenticated_status_delete_and_repeat_without_demo_dependencies(self):
        code, record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        lab = record['id']
        self.assertEqual(record['state'], 'running')
        self.assertEqual(record['provenance'], IDENTITY)
        with patch.dict(os.environ, {'DRYDOCK_LAB_PASSWORD': 'test-only'}), \
             patch('drydock.flow.eapi', side_effect=lambda host, password, commands:
                   [{'hostname': host['name']}, {'version': 'test'}]):
            code, result = self.invoke('lab', 'status', lab)
        self.assertEqual(code, 0)
        self.assertTrue(result['ready'])
        self.assertEqual({host['name'] for host in result['inventory']}, NODES)
        for _ in range(2):
            code, result = self.invoke('lab', 'delete', lab)
            self.assertEqual(code, 0)
            self.assertTrue(result['deleted'])
        self.assertFalse(self.backend.namespaces)

    def test_failed_creation_cleans_up_and_returns_failure(self):
        self.backend.fail_namespace = True
        code, result = self.invoke(*self.create_args)
        self.assertEqual(code, 1)
        self.assertTrue(result['cleanup']['deleted'])
        self.assertFalse(self.backend.namespaces)

    def test_expired_lab_is_removed_by_reap(self):
        code, record = self.invoke(*self.create_args)
        self.assertEqual(code, 0)
        with patch('drydock.lifecycle.now', return_value=record['expires_at'] + 1):
            code, result = self.invoke('reap')
        self.assertEqual(code, 0)
        self.assertTrue(result['cleanup'][0]['deleted'])
        self.assertFalse(self.backend.namespaces)

    def test_core_help_excludes_demo_commands(self):
        parser = cli.parser()
        parser.prog = 'drydock'
        help_text = parser.format_help()
        self.assertIn('{lab,reap}', help_text)
        self.assertNotIn('infra', help_text)
        self.assertNotIn('test', help_text)

    def test_context_is_explicit_even_inside_kubernetes(self):
        with patch.dict(os.environ, {'KUBERNETES_SERVICE_HOST': 'test-cluster'}):
            self.assertEqual(Environment.load(self.environment).kube_command('get', 'namespaces'),
                             [*ENV.kube_command(), 'get', 'namespaces'])

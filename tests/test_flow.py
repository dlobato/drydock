"""Acceptance and cleanup tests for the optional six-switch demo."""

from pathlib import Path
import signal
import tempfile
import unittest
from unittest.mock import patch

from examples.demo import flow
from drydock.flow import Canceled, cancellation, connections
from test_lifecycle import ENV, IDENTITY, NODES, make_bundle, switch_pods


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

    def test_one_reachability_result_cannot_replace_another(self):
        from collections import Counter
        expected = Counter({('leaf1', 'VerifyReachability', 'underlay'): 1,
                            ('leaf1', 'VerifyReachability', 'peers'): 1})
        rows = [{'name': 'leaf1', 'test': 'VerifyReachability', 'description': 'underlay', 'result': 'success'}] * 2
        self.assertFalse(flow.acceptance(rows, expected)['passed'])


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
                    raise Canceled('cancel')
                return flow.acceptance(results, required)

            def wait_for(action, timeout, *args):
                result = action()
                if result is None:
                    raise TimeoutError('timeout')
                return result

            with patch('examples.demo.flow.prepare', return_value=(Path(directory), expected)), \
                 patch('examples.demo.flow.create_lab', side_effect=RuntimeError if failure == 'allocation' else None), \
                 patch('drydock.flow.snapshot', return_value=({}, switch_pods(), [])), \
                 patch('drydock.flow.connections', side_effect=ValueError if failure == 'discovery' else None,
                       return_value=connections(switch_pods())), \
                 patch('drydock.flow.probe', side_effect=OSError if failure == 'probe' else None,
                       return_value={n: 'test' for n in NODES}), \
                 patch('examples.demo.flow.wait_for', side_effect=wait_for), \
                 patch('examples.demo.flow.converge', side_effect=converge), \
                 patch('examples.demo.flow.network_diagnostics', return_value={}), \
                 patch('examples.demo.flow.diagnostics', return_value={}), \
                 patch('examples.demo.flow.reports', side_effect=OSError if failure == 'report' else flow.reports), \
                 patch('examples.demo.flow.cleanup', return_value={'deleted': cleanup_success}) as cleanup:
                result = flow.test_flow(ENV, bundle, directory, IDENTITY, 'TOP-SECRET', directory)
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
        for failure in ('allocation', 'discovery', 'probe', 'anta', 'report', 'timeout', 'cancel'):
            with self.subTest(failure=failure):
                self.assertFalse(self.run_flow(failure)['passed'])

    def test_invalid_deadlines_do_not_allocate(self):
        with tempfile.TemporaryDirectory() as directory, patch('examples.demo.flow.create_lab') as create:
            bundle = make_bundle(directory)
            with self.assertRaises(ValueError):
                flow.test_flow(ENV, bundle, directory, IDENTITY, 'secret', directory, lifetime=1)
            create.assert_not_called()

    def test_sigterm_uses_cancellation_path(self):
        previous = signal.getsignal(signal.SIGTERM)
        with self.assertRaises(Canceled), cancellation():
            signal.raise_signal(signal.SIGTERM)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

if __name__ == '__main__':
    unittest.main()

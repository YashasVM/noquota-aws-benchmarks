import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

import fetch


JOB = 'a' * 64
OTHER = 'b' * 64


def sample(index, **changes):
    return dict(job_id=JOB, observed_at=f'2026-11-07T00:{index:02d}:00Z',
                state='running', confirmed=index, network_in_bytes=index * 1_000_000,
                **changes)


def page(rows, more=False, cursor=None, job=JOB):
    return dict(job_id=job, samples=rows, has_more=more, next_before=cursor)


class FetchBenchmarkTests(unittest.TestCase):
    def test_paginated_history_exports_only_safe_fields_in_time_order(self):
        rows = [sample(index) for index in range(4)]
        rows[2].update(filename='private-photo.jpg', checkpoint={'ciphertext': 'secret'},
                       destination='private@example.com')
        responses = [{'current': rows[3]}, page(rows[2:], True, rows[2]['observed_at']),
                     page(rows[:2])]
        with tempfile.TemporaryDirectory() as temporary, \
                patch.object(fetch, 'get_json', side_effect=responses) as request:
            root = Path(temporary)
            self.assertEqual(fetch.refresh(root, 'private-view-key'), 4)
            summary = json.loads((root / 'summary.json').read_text())
            csv = (root / 'samples.csv').read_text()
            self.assertEqual(summary['observations'], 4)
            self.assertEqual(summary['last_observed_at'], rows[3]['observed_at'])
            self.assertLess(csv.index(rows[0]['observed_at']), csv.index(rows[3]['observed_at']))
            self.assertNotIn('private', csv + json.dumps(summary))
            self.assertNotIn('checkpoint', csv)
            self.assertNotIn(JOB, csv)
            self.assertEqual(request.call_args_list[0].args, ('private-view-key', 'snapshot'))
            self.assertEqual(request.call_args_list[2].args[1],
                             'history?job_id=' + JOB + '&limit=500&before=2026-11-07T00%3A02%3A00Z')

    def test_failed_or_invalid_later_page_preserves_both_existing_files(self):
        invalid_pages = [OSError('network failed'), page([sample(0)], job=OTHER),
                         page([{**sample(0), 'job_id': OTHER}]),
                         page([{**sample(0), 'confirmed': 'private string'}]),
                         page([sample(2)]), page([sample(1), sample(0)]),
                         page([sample(0)], True, sample(1)['observed_at'])]
        for invalid in invalid_pages:
            with self.subTest(invalid=type(invalid).__name__), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                for name in ('samples.csv', 'summary.json'):
                    (root / name).write_text('original ' + name)
                responses = [{'current': sample(3)}, page([sample(2), sample(3)], True,
                             sample(2)['observed_at']), invalid]
                with patch.object(fetch, 'get_json', side_effect=responses), self.assertRaises(Exception):
                    fetch.refresh(root, 'private-view-key')
                self.assertEqual((root / 'samples.csv').read_text(), 'original samples.csv')
                self.assertEqual((root / 'summary.json').read_text(), 'original summary.json')

    def test_rejects_empty_malformed_and_stuck_history(self):
        for invalid in [page([]), {**page([sample(0)]), 'has_more': 1},
                        page([{**sample(0), 'observed_at': '2026-11-07T00:00:00+00:00'}]),
                        page([sample(1), sample(1)]), page([sample(0)], True, None)]:
            with self.subTest(invalid=invalid), \
                    patch.object(fetch, 'get_json', side_effect=[{'current': sample(1)}, invalid]), \
                    self.assertRaises((ValueError, TypeError)):
                fetch.download_samples('private-view-key')

    def test_key_stays_in_header_and_redirects_are_refused(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"current":{}}'
        opener = Mock()
        opener.open.return_value = response
        with patch.object(fetch, 'build_opener', return_value=opener):
            self.assertEqual(fetch.get_json('private-view-key', 'snapshot'), {'current': {}})
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url, fetch.BASE + 'snapshot')
        self.assertNotIn('private-view-key', request.full_url)
        self.assertEqual(request.get_header('Authorization'), 'Bearer private-view-key')
        self.assertEqual(opener.open.call_args.kwargs['timeout'], 30)
        with self.assertRaises(ValueError):
            fetch.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://elsewhere.invalid/')
        with patch.object(fetch, 'get_json') as request:
            for key in (None, '', ' ', 'key\nInjected: value'):
                with self.assertRaises(ValueError):
                    fetch.download_samples(key)
            request.assert_not_called()

    def test_workflow_refuses_unexpected_staged_file(self):
        workflow = (Path(__file__).resolve().parents[1]
                    / '.github/workflows/refresh-benchmarks.yml').read_text()
        self.assertNotIn('git push origin HEAD:main', workflow)
        self.assertIn('git push origin HEAD:automation/measurements', workflow)
        self.assertIn('gh pr create --draft', workflow)
        script = workflow.split("python3 - <<'PY'\n", 1)[1].split('\n          PY', 1)[0]
        script = '\n'.join(line[10:] for line in script.splitlines())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(['git', 'init', '-q'], cwd=root, check=True)
            (root / 'data').mkdir()
            (root / 'data/samples.csv').write_text('fixture')
            subprocess.run(['git', 'add', 'data/samples.csv'], cwd=root, check=True)
            allowed = subprocess.run(['python3', '-c', script], cwd=root, capture_output=True)
            self.assertEqual(allowed.returncode, 0, allowed.stderr)
            (root / 'unexpected.txt').write_text('fixture')
            subprocess.run(['git', 'add', 'unexpected.txt'], cwd=root, check=True)
            refused = subprocess.run(['python3', '-c', script], cwd=root, capture_output=True)
            self.assertNotEqual(refused.returncode, 0)
            self.assertIn(b'Unexpected staged changes', refused.stderr)


if __name__ == '__main__':
    unittest.main()

"""Regressions for real recorder values and incomplete capture rejection."""
import csv
import io
import tempfile
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import trace_diff


class RecorderContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        fixture = Path(__file__).parent / 'fixtures/trace/vanilla.trace.csv'
        self.row = next(csv.DictReader(fixture.read_text().splitlines()))

    def parse(self, name, changes=None, prefix='', suffix=''):
        row = dict(self.row)
        row.update(changes or {})
        text = io.StringIO()
        text.write(prefix)
        writer = csv.DictWriter(text, fieldnames=trace_diff.EXPECTED_COLUMNS, lineterminator='\n')
        writer.writeheader()
        writer.writerow(row)
        text.write(suffix)
        path = Path(self.temp.name) / name
        path.write_text(text.getvalue(), encoding='utf8')
        return trace_diff.parse_trace_file(str(path))

    def test_exact_values_across_scalar_and_compound_fields(self):
        for field, left, right in [
            ('pos_x', '-0', '0'),
            ('speed', 'motion=-0:1', 'motion=0:1'),
            ('work', 'FLOAT_TEST=-0', 'FLOAT_TEST=0'),
            ('hitboxes', '0/0/1/45/10/0/0/2/-0/0/0/0/0/0', '0/0/1/45/10/0/0/2/0/0/0/0/0/0'),
            ('work', 'INT_TEST=9007199254740992', 'INT_TEST=9007199254740993'),
            ('pos_x', 'NaN', '1'),
        ]:
            with self.subTest(field=field, left=left):
                a = self.parse('a.csv', {field: left})
                b = self.parse('b.csv', {field: right})
                self.assertTrue(trace_diff.diff_traces(a, b, set()))

    def test_same_nan_and_infinity_equal(self):
        for val in ['NaN', 'inf', '-inf']:
            a = self.parse('a.csv', {'pos_x': val, 'speed': 'sum=' + val + ':0'})
            b = self.parse('b.csv', {'pos_x': val, 'speed': 'sum=' + val + ':0'})
            self.assertEqual(trace_diff.diff_traces(a, b, set()), [])

    def test_tolerance_is_opt_in(self):
        a = self.parse('a.csv', {'pos_x': '-0'})
        b = self.parse('b.csv', {'pos_x': '0'})
        self.assertEqual(trace_diff.diff_traces(a, b, set(), 1e-6), [])
        self.assertFalse(trace_diff.values_equal('NaN', '1', 1e-6))

    def test_duplicates_rejected(self):
        for field, value in [('speed', 'sum=0:0;sum=1:1'), ('work', 'X=1;X=2'),
                             ('hitboxes', ';'.join(['0/0/1/45/10/0/0/2/0/0/0/0/0/0'] * 2))]:
            with self.subTest(field=field), self.assertRaises(trace_diff.ParseError):
                self.parse('bad.csv', {field: value})

    def test_recorder_requires_valid_completion(self):
        for footer in ['', '# invalid missing callbacks\n', '# complete frames=2 rows=1\n',
                       '# complete frames=1 rows=2\n']:
            with self.subTest(footer=footer), self.assertRaises(trace_diff.ParseError):
                self.parse('bad.csv', prefix='# pmclone_trace v0.1.1\n', suffix=footer)
        self.assertTrue(self.parse('good.csv', prefix='# pmclone_trace v0.1.1\n',
                                   suffix='# complete frames=1 rows=1\n'))

    def test_empty_trace_rejected(self):
        path = Path(self.temp.name) / 'empty.csv'
        path.write_text(','.join(trace_diff.EXPECTED_COLUMNS) + '\n')
        with self.assertRaises(trace_diff.ParseError):
            trace_diff.parse_trace_file(str(path))


if __name__ == '__main__':
    unittest.main()

from torch.testing._internal import expecttest
from torch.testing._internal.common_utils import TestCase, run_tests

import string
import textwrap
import doctest
from typing import Dict, Any
import traceback

import hypothesis
from hypothesis.strategies import text, integers, composite, sampled_from, booleans


@composite
def text_lineno(draw):
    t = draw(text("a\n"))
    lineno = draw(integers(min_value=1, max_value=t.count("\n") + 1))
    return (t, lineno)


class TestExpectTest(TestCase):
    @hypothesis.given(text_lineno())
    def test_nth_line_ref(self, t_lineno):
        t, lineno = t_lineno
        hypothesis.event("lineno = {}".format(lineno))

        def nth_line_ref(src, lineno):
            xs = src.split("\n")[:lineno]
            xs[-1] = ''
            return len("\n".join(xs))
        self.assertEqual(expecttest.nth_line(t, lineno), nth_line_ref(t, lineno))

    @hypothesis.given(text(string.printable), booleans(), sampled_from(['"', "'"]), booleans())
    def test_replace_string_literal_roundtrip(self, t, raw, quote, lineno_at_start):
        if raw:
            hypothesis.assume(expecttest.ok_for_raw_triple_quoted_string(t, quote=quote))
        prog = """\
        r = {r}{quote}placeholder{quote}
        r2 = {r}{quote}placeholder2{quote}
        r3 = {r}{quote}placeholder3{quote}
        """.format(r='r' if raw else '', quote=quote * 3)
        new_prog = expecttest.replace_string_literal(
            textwrap.dedent(prog), 2, t, lineno_at_start=lineno_at_start)[0]
        ns : Dict[str, Any] = {}
        exec(new_prog, ns)
        msg = "program was:\n{}".format(new_prog)
        self.assertEqual(ns['r'], 'placeholder', msg=msg)  # noqa: F821
        self.assertEqual(ns['r2'], expecttest.normalize_nl(t), msg=msg)  # noqa: F821
        self.assertEqual(ns['r3'], 'placeholder3', msg=msg)  # noqa: F821

    def test_sample_lineno_at_end(self):
        prog = r"""
single_single('''0''')
single_multi('''1''')
multi_single('''\
2
''')
multi_multi_less('''\
3
4
''')
multi_multi_same('''\
5
''')
multi_multi_more('''\
6
''')
"""
        # NB: These are the end of the statements, not beginning
        # TODO: Test other permutations of these edits
        edits = [(2, "a"),
                 (3, "b\n"),
                 (6, "c"),
                 (10, "d\n"),
                 (13, "e\n"),
                 (16, "f\ng\n")]
        history = expecttest.EditHistory()
        fn = 'not_a_real_file.py'
        for lineno, actual in edits:
            lineno = history.adjust_lineno(fn, lineno)
            prog, delta = expecttest.replace_string_literal(
                prog, lineno, actual, lineno_at_start=False)
            history.record_edit(fn, lineno, delta)
        self.assertExpectedInline(prog, r"""
single_single('''a''')
single_multi('''\
b
''')
multi_single('''c''')
multi_multi_less('''\
d
''')
multi_multi_same('''\
e
''')
multi_multi_more('''\
f
g
''')
""")

    def test_sample_lineno_at_start(self):
        prog = r"""
single_single('''0''')
single_multi('''1''')
multi_single('''\
2
''')
multi_multi_less('''\
3
4
''')
multi_multi_same('''\
5
''')
multi_multi_more('''\
6
''')
"""
        # NB: These are the beginning of the statements
        edits = [(2, "a"),
                 (3, "b\n"),
                 (4, "c"),
                 (7, "d\n"),
                 (11, "e\n"),
                 (14, "f\ng\n")]
        history = expecttest.EditHistory()
        fn = 'not_a_real_file.py'
        for lineno, actual in edits:
            lineno = history.adjust_lineno(fn, lineno)
            prog, delta = expecttest.replace_string_literal(
                prog, lineno, actual, lineno_at_start=True)
            history.record_edit(fn, lineno, delta)
        self.assertExpectedInline(prog, r"""
single_single('''a''')
single_multi('''\
b
''')
multi_single('''c''')
multi_multi_less('''\
d
''')
multi_multi_same('''\
e
''')
multi_multi_more('''\
f
g
''')
""")

    def test_lineno_assumptions(self):
        def get_tb(s):
            return traceback.extract_stack(limit=2)

        tb1 = get_tb("")
        tb2 = get_tb("""a
b
c""")

        if expecttest.LINENO_AT_START:
            # tb2's stack starts on the next line
            self.assertEqual(tb1[0].lineno + 1, tb2[0].lineno)
        else:
            # starts at the end here
            self.assertEqual(tb1[0].lineno + 1 + 2, tb2[0].lineno)


def load_tests(loader, tests, ignore):
    tests.addTests(doctest.DocTestSuite(expecttest))
    return tests


if __name__ == '__main__':
    run_tests()

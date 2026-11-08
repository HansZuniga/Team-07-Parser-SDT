"""
End-to-end tests (issue #10): every program in tests/cases/ is run through
the real command line (main.py --file <case> --sdt) and its full output
must match the case's .expected file.

Lexical cases always run, because lexical errors stop the process before
the parser loads its table. The other categories need the team grammar
and table in resources/parser/ and are skipped until they are there.
"""

import importlib.util
from pathlib import Path

import pytest

from clr1_parser import GRAMMAR_PATH, TABLE_PATH

CASES_DIR = Path(__file__).resolve().parent / "cases"

_spec = importlib.util.spec_from_file_location("run_cases", CASES_DIR / "run_cases.py")
run_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_cases)

HAVE_TABLE = GRAMMAR_PATH.is_file() and TABLE_PATH.is_file()
CASES = run_cases.case_files()


def case_id(case):
    return run_cases.relative(case)


@pytest.mark.parametrize("case", CASES, ids=case_id)
def test_case_output_matches_expected(case):
    if case.parent.name != "lexical" and not HAVE_TABLE:
        pytest.skip("team grammar/table not in resources/parser/ yet")
    assert run_cases.actual_output(case) == run_cases.expected_output(case)


def test_every_category_has_cases():
    for category, _ in run_cases.CATEGORIES:
        assert list((CASES_DIR / category).glob("*.c")), category


def test_every_case_has_expected_output_and_description():
    described = run_cases.descriptions()
    for case in CASES:
        assert case.with_suffix(".expected").is_file(), case
        assert described.get(case_id(case)), case
    assert set(described) == {case_id(case) for case in CASES}


@pytest.mark.parametrize(
    "category, first_line",
    [
        ("valid", "Parsing Success!"),
        ("syntax", "Parsing error in line "),
        ("semantic", "Parsing Success!"),
        ("lexical", "Lexical error in line "),
    ],
)
def test_expected_outputs_follow_the_category(category, first_line):
    # Guards the .expected files themselves against copy/paste mistakes.
    second = {"valid": "SDT Verified!", "semantic": "SDT error in line "}
    for case in (CASES_DIR / category).glob("*.c"):
        lines = run_cases.expected_output(case)
        assert lines[0].startswith(first_line), case
        if category in second:
            assert len(lines) == 2 and lines[1].startswith(second[category]), case
        else:
            assert len(lines) == 1, case

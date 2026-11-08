"""
Tests for the CLR(1) parser engine (issue #5).

Two groups:

1. A tiny hand-checked grammar, so the engine is tested on its own:

       0  S -> L
       1  L -> L x
       2  L -> epsilon

   Its CLR(1) table (computed by hand):

       state 0:  x -> r2   $ -> r2    GOTO L -> 1
       state 1:  x -> s2   $ -> acc
       state 2:  x -> r1   $ -> r1

2. The team grammar and ACTION/GOTO table (productions 0-50, states 0-160)
   from resources/parser/. These tests are skipped if those files are not
   in the repository yet.
"""

import pytest

from clr1_parser import (
    GRAMMAR_PATH,
    TABLE_PATH,
    ParseError,
    Parser,
    ParsingTable,
    TableError,
)
from lexer import Token
from token_stream import LexicalError, Terminal, tokenize_source

# ---------------------------------------------------------------------------
# Tiny grammar
# ---------------------------------------------------------------------------

TINY_GRAMMAR = [
    {"id": 0, "lhs": "S", "rhs": ["L"]},
    {"id": 1, "lhs": "L", "rhs": ["L", "x"]},
    {"id": 2, "lhs": "L", "rhs": []},
]

TINY_TABLE = {
    "action": [
        {"state": 0, "terminal": "x", "actions": [["r", 2]]},
        {"state": 0, "terminal": "$", "actions": [["r", 2]]},
        {"state": 1, "terminal": "x", "actions": [["s", 2]]},
        {"state": 1, "terminal": "$", "actions": [["acc", 0]]},
        {"state": 2, "terminal": "x", "actions": [["r", 1]]},
        {"state": 2, "terminal": "$", "actions": [["r", 1]]},
    ],
    "goto": [{"state": 0, "nonterminal": "L", "target": 1}],
}


def tiny_parser():
    return Parser(ParsingTable.from_data(TINY_GRAMMAR, TINY_TABLE))


def terminals_from(symbols, lines=None):
    """Build a terminal list (ending in $) without running the lexer."""
    lines = lines or [1] * len(symbols)
    result = [
        Terminal(s, Token("IDENTIFIER", s, line, i + 1), line, i + 1)
        for i, (s, line) in enumerate(zip(symbols, lines))
    ]
    last_line = lines[-1] if lines else 1
    result.append(Terminal("$", None, last_line, len(symbols) + 1))
    return result


def test_tiny_grammar_accepts_empty_input():
    result = tiny_parser().parse(terminals_from([]))
    assert result.message == "Parsing Success!"
    assert result.tree.symbol == "L"
    assert result.tree.children == []          # L -> epsilon


def test_tiny_grammar_left_recursion_builds_nested_tree():
    tree = tiny_parser().parse(terminals_from(["x", "x"])).tree
    # L -> L x, where the inner L -> L x, and the innermost L -> epsilon
    assert [c.symbol for c in tree.children] == ["L", "x"]
    inner = tree.children[0]
    assert [c.symbol for c in inner.children] == ["L", "x"]
    assert inner.children[0].children == []
    assert tree.production.id == 1


def test_trace_records_shift_reduce_goto_and_accept():
    result = tiny_parser().parse(terminals_from(["x"]), trace=True)
    actions = [step.action for step in result.steps]
    assert actions == [
        "reduce 2 (L -> epsilon), goto 1",
        "shift 2",
        "reduce 1 (L -> L x), goto 1",
        "accept",
    ]
    # The stack shown is the one before each action.
    assert [step.states for step in result.steps] == [(0,), (0, 1), (0, 1, 2), (0, 1)]
    assert [step.lookahead for step in result.steps] == ["x", "x", "$", "$"]


def test_no_trace_by_default():
    assert tiny_parser().parse(terminals_from(["x"])).steps is None


def test_unexpected_terminal_is_a_parse_error():
    with pytest.raises(ParseError) as info:
        tiny_parser().parse(terminals_from(["x", "y"], lines=[1, 1]))
    error = info.value
    assert str(error) == "Parsing error in line 1"
    assert error.terminal.symbol == "y"
    assert error.state == 2
    assert error.expected == ["$", "x"]


def test_error_on_a_new_line_without_semicolon_in_the_grammar():
    # The tiny grammar has no ';', so the error stays on the token's line.
    with pytest.raises(ParseError) as info:
        tiny_parser().parse(terminals_from(["x", "y"], lines=[1, 2]))
    assert info.value.line == 2


def test_parse_error_keeps_the_trace():
    with pytest.raises(ParseError) as info:
        tiny_parser().parse(terminals_from(["y"]), trace=True)
    assert info.value.steps[-1].action == "error"


def test_input_must_end_with_end_of_input():
    terminals = terminals_from(["x"])[:-1]
    with pytest.raises(ValueError):
        tiny_parser().parse(terminals)


def test_table_with_a_conflict_is_rejected():
    table = {
        "action": [{"state": 0, "terminal": "x", "actions": [["s", 1], ["r", 2]]}],
        "goto": [],
    }
    with pytest.raises(TableError):
        ParsingTable.from_data(TINY_GRAMMAR, table)


def test_reduce_by_unknown_production_is_rejected():
    table = {
        "action": [{"state": 0, "terminal": "x", "actions": [["r", 99]]}],
        "goto": [],
    }
    with pytest.raises(TableError):
        ParsingTable.from_data(TINY_GRAMMAR, table)


def test_missing_table_file_is_reported(tmp_path):
    with pytest.raises(TableError):
        ParsingTable.from_files(tmp_path / "g.json", tmp_path / "t.json")


# ---------------------------------------------------------------------------
# Team grammar (productions 0-50, states 0-160)
# ---------------------------------------------------------------------------

team_table = pytest.mark.skipif(
    not (GRAMMAR_PATH.is_file() and TABLE_PATH.is_file()),
    reason="team grammar/table not in resources/parser/ yet",
)


@pytest.fixture(scope="module")
def parser():
    return Parser()


def parse(parser, source, **kwargs):
    return parser.parse(tokenize_source(source), **kwargs)


def error_line(parser, source):
    with pytest.raises(ParseError) as info:
        parse(parser, source)
    return info.value.line


FULL_PROGRAM = """\
int main() {
    int a = 10;
    float b = 2.5;
    char c = 'z';
    int d;
    d = a % 3 + -a * (2 - 1);
    if (a > 5) { a = a - 1; } else { b = b * 2.0; }
    if (a) if (b) a = 1; else a = 2;
    while (a != 0) a = a - 1;
    while (!(a >= 10)) { a = a + 1; }
    { int e = 1; ; }
    return a == 10;
}
"""


@team_table
def test_team_table_loads(parser):
    assert len(parser.table.productions) == 51
    assert len(parser.table.action) == 1305
    assert len(parser.table.goto) == 221


@team_table
@pytest.mark.parametrize(
    "source",
    [
        FULL_PROGRAM,
        "int main() { }",
        "int main() { return 0; }",
        'int main() { char s; s = "hola"; }',
        "int main() { if (1) if (2) ; else ; }",   # dangling else
        "int main() { while (1) if (0) ; }",
    ],
)
def test_valid_programs_are_accepted(parser, source):
    assert parse(parser, source).message == "Parsing Success!"


@team_table
def test_tree_root_and_leaves_follow_the_source(parser):
    tree = parse(parser, FULL_PROGRAM).tree
    assert tree.symbol == "Program"
    assert tree.production.id == 1

    def leaves(node):
        if node.is_terminal:
            return [node.lexeme]
        return [lexeme for child in node.children for lexeme in leaves(child)]

    terminals = tokenize_source(FULL_PROGRAM)[:-1]
    assert leaves(tree) == [t.lexeme for t in terminals]


@team_table
def test_operator_precedence_in_the_tree(parser):
    # 1 + 2 * 3: the '*' must be below the '+' (Add -> Add + Mul).
    tree = parse(parser, "int main() { return 1 + 2 * 3; }").tree
    simple = tree.children[4].children[1].children[1]   # Block/Items/Item
    while simple.symbol != "Simple":
        simple = simple.children[0]
    add = simple.children[1].children[0].children[0].children[0]
    assert add.symbol == "Add"
    assert [c.symbol for c in add.children] == ["Add", "+", "Mul"]
    assert [c.symbol for c in add.children[2].children] == ["Mul", "*", "Unary"]


@team_table
def test_missing_semicolon_is_reported_on_its_own_line(parser):
    assert error_line(parser, "int main() {\n    int x = 5\n    return x;\n}") == 2


@team_table
@pytest.mark.parametrize(
    "source",
    [
        "int main() {\n  int x;\n  x = 1\n  x = 2;\n}",
        "int main() {\n  int x;\n  return x\n}",
        "int main() {\n  int x;\n  float y = 2.5\n  while (x) ;\n}",
    ],
)
def test_missing_semicolon_at_end_of_line_3(parser, source):
    assert error_line(parser, source) == 3


@team_table
def test_missing_semicolon_before_closing_brace_on_same_line(parser):
    assert error_line(parser, "int main() {\n    x = 1 }") == 2


@team_table
def test_unexpected_token_at_start_of_line_is_reported_on_that_line(parser):
    # ';' is not expected after '{', so the previous-line rule must not apply.
    assert error_line(parser, "int main() {\n) ;\n}") == 2


@team_table
@pytest.mark.parametrize(
    "source, line",
    [
        ("int main() {\n  x = ;\n}", 2),
        ("int main() {\n  int = 3;\n}", 2),
        ("int main() {\n  if x > 0) x = 1;\n}", 2),
        ("int main() {\n  x += 1;\n}", 2),
        ("int main() {\n  foo(1);\n}", 2),
        ("main() { }", 1),
        ("int main() {\n  return 0;\n", 2),     # missing '}' at end of file
        ("int main() { } int x;", 1),
        ("", 1),
    ],
)
def test_syntax_errors_report_the_line(parser, source, line):
    assert error_line(parser, source) == line


@team_table
def test_lexical_errors_never_reach_the_parser(parser):
    with pytest.raises(LexicalError) as info:
        parse(parser, "int main() {\n  int x = 3 @ 4;\n}")
    assert str(info.value) == "Lexical error in line 2"


@team_table
def test_error_details_name_the_expected_terminals(parser):
    with pytest.raises(ParseError) as info:
        parse(parser, "int main() { x = ; }")
    details = info.value.details()
    assert "unexpected ';'" in details
    assert "ID" in details and "INT" in details


@team_table
def test_long_program_tree_does_not_hit_the_recursion_limit(parser):
    source = "int main() { int x;" + " x = 1;" * 3000 + " }"
    tree = parse(parser, source).tree
    assert tree.line == 1
    assert len(tree.pretty().splitlines()) > 3000

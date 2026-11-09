"""
Extra tests for the test suite (issue #10), run with the team grammar and
ACTION/GOTO table (productions 0-50, states 0-160):

1. SHIFT/REDUCE behavior and state transitions on the real table, compared
   step by step with the trace of the Model Designer document
   "3. Tabla CLR(1) ACTION/GOTO" for  int main(){int x;}
2. A parse tree is generated for every valid case in tests/cases/valid/,
   with Program as root and the tokens of the program as its leaves.
3. The professor's example  int x = 10;  : alone it is not a Program
   (Parsing error in line 1); inside main it passes parser and SDT.

These tests are skipped if resources/parser/ does not have the Model
Designer files yet.
"""

from pathlib import Path

import pytest

from clr1_parser import GRAMMAR_PATH, TABLE_PATH, ParseError, Parser
from sdt import SemanticAnalyzer
from token_stream import tokenize_file, tokenize_source

pytestmark = pytest.mark.skipif(
    not (GRAMMAR_PATH.is_file() and TABLE_PATH.is_file()),
    reason="team grammar/table not in resources/parser/ yet",
)

VALID_CASES = sorted(
    (Path(__file__).resolve().parent / "cases" / "valid").glob("*.c")
)


@pytest.fixture(scope="module")
def parser():
    return Parser()


def leaves(node):
    """Terminal leaves of the tree, left to right (epsilon nodes add none)."""
    if node.is_terminal:
        return [node]
    return [leaf for child in node.children for leaf in leaves(child)]


# ---------------------------------------------------------------------------
# 1. SHIFT / REDUCE and state transitions with the team table
# ---------------------------------------------------------------------------

# (stack of states before the action, lookahead, action)
EXPECTED_TRACE = [
    ((0,), "int", "shift 2"),
    ((0, 2), "main", "shift 3"),
    ((0, 2, 3), "(", "shift 4"),
    ((0, 2, 3, 4), ")", "shift 5"),
    ((0, 2, 3, 4, 5), "{", "shift 7"),
    ((0, 2, 3, 4, 5, 7), "int", "reduce 4 (Items -> epsilon), goto 8"),
    ((0, 2, 3, 4, 5, 7, 8), "int", "shift 22"),
    ((0, 2, 3, 4, 5, 7, 8, 22), "ID", "reduce 8 (Type -> int), goto 17"),
    ((0, 2, 3, 4, 5, 7, 8, 17), "ID", "shift 28"),
    ((0, 2, 3, 4, 5, 7, 8, 17, 28), ";", "reduce 12 (Init -> epsilon), goto 50"),
    ((0, 2, 3, 4, 5, 7, 8, 17, 28, 50), ";", "shift 87"),
    ((0, 2, 3, 4, 5, 7, 8, 17, 28, 50, 87), "}",
     "reduce 7 (Decl -> Type ID Init ;), goto 11"),
    ((0, 2, 3, 4, 5, 7, 8, 11), "}", "reduce 5 (Item -> Decl), goto 13"),
    ((0, 2, 3, 4, 5, 7, 8, 13), "}", "reduce 3 (Items -> Items Item), goto 8"),
    ((0, 2, 3, 4, 5, 7, 8), "}", "shift 26"),
    ((0, 2, 3, 4, 5, 7, 8, 26), "$", "reduce 2 (Block -> { Items }), goto 6"),
    ((0, 2, 3, 4, 5, 6), "$",
     "reduce 1 (Program -> int main ( ) Block), goto 1"),
    ((0, 1), "$", "accept"),
]


def test_shift_reduce_trace_matches_the_team_table(parser):
    result = parser.parse(tokenize_source("int main() { int x; }"), trace=True)
    actual = [(tuple(s.states), s.lookahead, s.action) for s in result.steps]
    assert actual == EXPECTED_TRACE


def test_reductions_do_not_consume_the_lookahead(parser):
    # A reduce keeps the same lookahead for the next step; only a shift
    # moves to the next terminal.
    steps = parser.parse(
        tokenize_source("int main() { int x; }"), trace=True
    ).steps
    for step, following in zip(steps, steps[1:]):
        if step.action.startswith("reduce"):
            assert following.lookahead == step.lookahead


def test_epsilon_reduction_pops_no_state(parser):
    steps = parser.parse(
        tokenize_source("int main() { int x; }"), trace=True
    ).steps
    for step, following in zip(steps, steps[1:]):
        if "epsilon" in step.action:
            # Nothing is popped: the stack only grows by the GOTO state.
            assert following.states[:-1] == step.states


def test_reduce_pops_the_length_of_the_right_hand_side(parser):
    steps = parser.parse(
        tokenize_source("int main() { int x; }"), trace=True
    ).steps
    decl = next(s for s in steps if s.action.startswith("reduce 7 "))
    after = steps[steps.index(decl) + 1]
    # Decl -> Type ID Init ;  pops 4 states and pushes GOTO[8, Decl] = 11.
    assert after.states == decl.states[:-4] + (11,)


# ---------------------------------------------------------------------------
# 2. A parse tree for every valid case
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("case", VALID_CASES, ids=lambda p: p.stem)
def test_every_valid_case_generates_a_parse_tree(parser, case):
    terminals = tokenize_file(case)
    tree = parser.parse(terminals).tree
    assert tree.symbol == "Program"
    assert tree.production.id == 1
    # The leaves are exactly the tokens of the program, in order.
    assert [(leaf.symbol, leaf.lexeme) for leaf in leaves(tree)] == [
        (t.symbol, t.lexeme) for t in terminals[:-1]
    ]


def test_there_are_ten_valid_cases():
    assert len(VALID_CASES) == 10


# ---------------------------------------------------------------------------
# 3. The professor's example: int x = 10;
# ---------------------------------------------------------------------------

def test_professor_example_alone_is_not_a_program(parser):
    # In state 0 only 'int' is valid -> state 2, which only accepts 'main'.
    with pytest.raises(ParseError) as info:
        parser.parse(tokenize_source("int x = 10;"))
    error = info.value
    assert str(error) == "Parsing error in line 1"
    assert error.state == 2
    assert error.terminal.symbol == "ID"
    assert error.expected == ["main"]


def test_professor_example_inside_main_passes_parser_and_sdt(parser):
    result = parser.parse(tokenize_source("int main() {\n    int x = 10;\n}"))
    assert result.message == "Parsing Success!"
    sdt = SemanticAnalyzer().analyze(result.tree)
    assert sdt.message == "SDT Verified!"
    (x,) = sdt.symbols.records
    assert (x.name, x.data_type, x.scope_id, x.line) == ("x", "int", 0, 2)
    assert (x.initializer_type, x.initializer_lexeme) == ("int", "10")

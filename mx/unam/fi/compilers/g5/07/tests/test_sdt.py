"""
Tests for the SDT / semantic analysis (issue #8).

The type policy and symbol table are tested on their own. The analysis
tests parse real programs with the team grammar, so they are skipped
until resources/parser/ has the Model Designer files.
"""

import pytest

from clr1_parser import GRAMMAR_PATH, TABLE_PATH, Parser
from sdt import (
    CHAR,
    FLOAT,
    INT,
    STRING,
    SemanticAnalyzer,
    SemanticError,
    SymbolTable,
    assignable,
    promote,
)
from token_stream import tokenize_source

# ---------------------------------------------------------------------------
# Type policy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "destination, source, expected",
    [
        (CHAR, CHAR, True), (CHAR, INT, False), (CHAR, FLOAT, False),
        (INT, CHAR, True), (INT, INT, True), (INT, FLOAT, False),
        (FLOAT, CHAR, True), (FLOAT, INT, True), (FLOAT, FLOAT, True),
        (INT, STRING, False), (CHAR, STRING, False), (FLOAT, STRING, False),
    ],
)
def test_compatibility_matrix(destination, source, expected):
    assert assignable(destination, source) is expected


def test_promotion():
    assert promote(CHAR) == INT
    assert promote(INT) == INT
    assert promote(FLOAT) == FLOAT


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------

def test_scopes_shadowing_and_records():
    table = SymbolTable()
    assert table.open_scope() == 0
    outer = table.declare("x", INT, 2, 5)
    assert table.open_scope() == 1
    inner = table.declare("x", FLOAT, 3, 11)
    assert table.lookup("x") is inner            # innermost first
    assert table.lookup_current("x") is inner
    table.close_scope()
    assert table.lookup("x") is outer            # inner scope closed
    assert table.records == [outer, inner]       # records survive closing
    assert (inner.scope_id, outer.scope_id) == (1, 0)


def test_lookup_of_unknown_name():
    table = SymbolTable()
    table.open_scope()
    assert table.lookup("nope") is None


# ---------------------------------------------------------------------------
# Analysis of real programs
# ---------------------------------------------------------------------------

pytestmark_team = pytest.mark.skipif(
    not (GRAMMAR_PATH.is_file() and TABLE_PATH.is_file()),
    reason="team grammar/table not in resources/parser/ yet",
)


@pytest.fixture(scope="module")
def parser():
    return Parser()


def analyze(parser, source):
    tree = parser.parse(tokenize_source(source)).tree
    return SemanticAnalyzer().analyze(tree)


def in_main(body):
    return "int main() {\n" + body + "\n}"


def semantic_error(parser, source):
    with pytest.raises(SemanticError) as info:
        analyze(parser, source)
    return info.value


# Every example from the team document "4. Reglas SDT" (body of main).
DOCUMENT_EXAMPLES = [
    ("int x=10; return x;", None),
    ('int x="hello";', "SEM004"),
    ("char c='a';", None),
    ("char c=65;", "SEM004"),
    ("char c='a'+1;", "SEM004"),
    ("char c='a'; c=c+1;", "SEM003"),
    ("char c='a'; int x=c+1;", None),
    ("int x; int x;", "SEM001"),
    ("y=1;", "SEM002"),
]


@pytestmark_team
@pytest.mark.parametrize("body, code", DOCUMENT_EXAMPLES)
def test_examples_from_the_team_document(parser, body, code):
    source = in_main(body)
    if code is None:
        assert analyze(parser, source).message == "SDT Verified!"
    else:
        assert semantic_error(parser, source).code == code


@pytestmark_team
@pytest.mark.parametrize(
    "body",
    [
        "int x = 1;\n{ float x = 2.5; }\nreturn x;",      # shadowing
        "int x = x;",                                      # inserted first
        "float f = 'a' + 1;",                              # widening
        "int x; x = -'a';",                                # promote(char) = int
        "int x = !2.5;",                                   # ! gives int
        "int b = 1.5 < 2;",                                # comparison gives int
        "int m = 'a' % 3;",                                # % with char
        "float f; f = 1 / 2 * 3.0;",
        "char c; if (c) c = 'b'; else c = 'd';",
        "int i = 0; while (i < 10) { int j = i; i = i + 1; }",
        "{ int a; { int b; a = b; } }",                    # outer name visible
        "return 'a';",                                     # char -> int
        "int x; { int x; { int x; } }",                    # each scope its own
        ";",
    ],
)
def test_valid_programs(parser, body):
    assert analyze(parser, in_main(body)).message == "SDT Verified!"


@pytestmark_team
@pytest.mark.parametrize(
    "body, code, line, lexeme",
    [
        ("int a;\nfloat a;", "SEM001", 3, "a"),
        ("int a;\n{ int b; }\nb = 1;", "SEM002", 4, "b"),
        ("int a = b;", "SEM002", 2, "b"),
        ("int a;\nif (a) { zz = 1; }", "SEM002", 3, "zz"),
        ("int a;\na = 2.5;", "SEM003", 3, "a"),
        ('char c;\nc = "s";', "SEM003", 3, "c"),
        ("int a = 1.5;", "SEM004", 2, "a"),
        ("float f = 1.5;\nint m = f % 2;", "SEM005", 3, "%"),
        ('int a = 1 + "s";', "SEM005", 2, "+"),
        ('int a = -"s";', "SEM005", 2, "-"),
        ('int a = "x" == "y";', "SEM005", 2, "=="),
        ('if ("a") ;', "SEM006", 2, "if"),
        ('while ("a") ;', "SEM006", 2, "while"),
        ("return 2.5;", "SEM007", 2, "return"),
        ('return "s";', "SEM007", 2, "return"),
    ],
)
def test_semantic_errors(parser, body, code, line, lexeme):
    error = semantic_error(parser, in_main(body))
    assert (error.code, error.line, error.lexeme) == (code, line, lexeme)
    assert str(error) == f"SDT error in line {line}"


@pytestmark_team
def test_only_the_first_error_is_reported(parser):
    error = semantic_error(parser, in_main("y = 1;\nint x; int x;"))
    assert (error.code, error.line) == ("SEM002", 2)


@pytestmark_team
def test_error_details_include_code_and_description(parser):
    error = semantic_error(parser, in_main('int x = "hello";'))
    assert error.details() == (
        "SDT error in line 2 (column 5, 'x'): "
        "SEM004 cannot initialize int 'x' with string"
    )


@pytestmark_team
def test_symbol_table_of_the_document_example(parser):
    # Example "del arbol a la tabla de simbolos" of the team document.
    source = (
        "int main() {\n"
        "    int x = 10;\n"
        "    float y = x + 2.5;\n"
        "    return x;\n"
        "}\n"
    )
    records = analyze(parser, source).symbols.records
    rows = [
        (s.name, s.data_type, s.scope_id, s.line,
         s.has_initializer, s.initializer_type, s.initializer_lexeme)
        for s in records
    ]
    assert rows == [
        ("x", INT, 0, 2, True, INT, "10"),
        ("y", FLOAT, 0, 3, True, FLOAT, None),    # expression, no literal
    ]


@pytestmark_team
def test_symbol_table_keeps_closed_scopes(parser):
    source = in_main("int x = 1;\n{ float x = 2.5; }\nreturn x;")
    records = analyze(parser, source).symbols.records
    assert [(s.name, s.data_type, s.scope_id) for s in records] == [
        ("x", INT, 0),
        ("x", FLOAT, 1),
    ]


@pytestmark_team
def test_symbol_table_is_available_after_an_error(parser):
    error = semantic_error(parser, in_main("int a;\nint a;"))
    assert [s.name for s in error.symbols.records] == ["a"]


@pytestmark_team
def test_long_program_does_not_hit_the_recursion_limit(parser):
    body = "int x = 0;\n" + "x = x + 1;\n" * 3000
    assert analyze(parser, in_main(body)).message == "SDT Verified!"

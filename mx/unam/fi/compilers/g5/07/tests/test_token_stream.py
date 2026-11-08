"""
Tests for the lexer -> CLR(1) parser bridge (issue #7).
"""

import pytest

from lexer import Lexer, Token
from token_stream import (
    END_OF_INPUT,
    LexicalError,
    Terminal,
    build_terminals,
    to_terminal,
    tokenize_file,
    tokenize_source,
)


def symbols(terminals):
    return [t.symbol for t in terminals]


# ---------------------------------------------------------------------------
# Mapping of each token category
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "token_type, lexeme, terminal",
    [
        ("KEYWORD", "int", "int"),
        ("KEYWORD", "while", "while"),
        ("IDENTIFIER", "x", "id"),
        ("IDENTIFIER", "main", "id"),
        ("CONSTANT", "10", "num"),
        ("CONSTANT", "3.5", "num"),
        ("LITERAL", "'a'", "char_lit"),
        ("LITERAL", '"hello"', "string_lit"),
        ("OPERATOR", "=", "="),
        ("OPERATOR", "<=", "<="),
        ("PUNCTUATION", ";", ";"),
        ("PUNCTUATION", "{", "{"),
    ],
)
def test_token_category_maps_to_terminal(token_type, lexeme, terminal):
    assert to_terminal(Token(token_type, lexeme, 1, 1)) == terminal


def test_unknown_token_type_is_rejected():
    with pytest.raises(ValueError):
        to_terminal(Token("ERROR", "@", 1, 1))


# ---------------------------------------------------------------------------
# Full flow: source code -> terminal sequence
# ---------------------------------------------------------------------------

def test_issue_7_example():
    terminals = tokenize_source("int x = 10;")
    assert symbols(terminals) == ["int", "id", "=", "num", ";", "$"]


def test_lexeme_line_and_column_are_preserved():
    terminals = tokenize_source("int x = 10;\n  x = x + 1;")
    x_use = terminals[5]
    assert (x_use.symbol, x_use.lexeme, x_use.line, x_use.column) == ("id", "x", 2, 3)
    assert x_use.token.type == "IDENTIFIER"


def test_token_order_is_preserved():
    source = "while (a <= b) { a = a + 1; }"
    terminals = tokenize_source(source)
    lexemes = [t.lexeme for t in terminals[:-1]]
    assert lexemes == ["while", "(", "a", "<=", "b", ")", "{",
                       "a", "=", "a", "+", "1", ";", "}"]


def test_full_supported_subset_program():
    source = (
        "int main() {\n"
        "    int a = 10;\n"
        "    float b = 2.5;\n"
        "    char c = 'z';\n"
        "    if (a > 5) { a = a - 1; } else { b = b * 2; }\n"
        "    while (a != 0) { a = a - 1; }\n"
        "    return 0;\n"
        "}\n"
    )
    terminals = tokenize_source(source)
    assert symbols(terminals) == [
        "int", "id", "(", ")", "{",
        "int", "id", "=", "num", ";",
        "float", "id", "=", "num", ";",
        "char", "id", "=", "char_lit", ";",
        "if", "(", "id", ">", "num", ")", "{", "id", "=", "id", "-", "num", ";", "}",
        "else", "{", "id", "=", "id", "*", "num", ";", "}",
        "while", "(", "id", "!=", "num", ")", "{", "id", "=", "id", "-", "num", ";", "}",
        "return", "num", ";",
        "}", "$",
    ]


# ---------------------------------------------------------------------------
# End-of-input symbol
# ---------------------------------------------------------------------------

def test_end_of_input_is_appended_exactly_once():
    terminals = tokenize_source("int x;")
    assert symbols(terminals).count(END_OF_INPUT) == 1
    assert terminals[-1].symbol == END_OF_INPUT
    assert terminals[-1].token is None
    assert terminals[-1].lexeme == "$"


def test_end_of_input_is_placed_after_the_last_token():
    terminals = tokenize_source("int x = 10;\nx = 5")
    end = terminals[-1]
    assert (end.line, end.column) == (2, 6)


def test_empty_source_produces_only_end_of_input():
    terminals = tokenize_source("")
    assert symbols(terminals) == ["$"]
    assert (terminals[0].line, terminals[0].column) == (1, 1)


# ---------------------------------------------------------------------------
# Lexical errors stop the process before parsing
# ---------------------------------------------------------------------------

def test_lexical_error_stops_before_parsing():
    with pytest.raises(LexicalError) as info:
        tokenize_source("int x = 10;\nint y = 3 @ 4;")
    assert str(info.value) == "Lexical error in line 2"
    assert info.value.line == 2


def test_lexical_error_reports_the_first_error_line_and_keeps_all_errors():
    with pytest.raises(LexicalError) as info:
        tokenize_source("int a = 1;\nint b = 12abc;\nchar c = 'xy';")
    assert info.value.line == 2
    assert [e.lexeme for e in info.value.errors] == ["12abc", "'xy'"]


def test_build_terminals_rejects_errors_from_any_lexer_run():
    lexer = Lexer()
    tokens = lexer.tokenize('x = "unterminated')
    with pytest.raises(LexicalError):
        build_terminals(tokens, lexer.errors)


def test_terminal_repr_is_readable():
    terminal = Terminal("id", Token("IDENTIFIER", "x", 3, 7), 3, 7)
    assert repr(terminal) == "Terminal('id', lexeme='x', line=3, column=7)"


def test_tokenize_file(tmp_path):
    source = tmp_path / "program.c"
    source.write_bytes(b"\xef\xbb\xbfchar c = 'a';")
    terminals = tokenize_file(source)
    assert symbols(terminals) == ["char", "id", "=", "char_lit", ";", "$"]

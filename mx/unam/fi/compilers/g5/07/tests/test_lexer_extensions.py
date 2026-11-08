"""
Tests for the lexer changes needed by the Parser & SDT scope (issue #1):
new keywords float/char/while, character literals and the
operators % and ! used by the CLR(1) grammar.
"""

from pathlib import Path

import pytest

from lexer import Lexer, DEFAULT_KEYWORDS

KEYWORDS_FILE = Path(__file__).resolve().parents[1] / "resources" / "keywords.txt"


def make_lexer():
    return Lexer(keywords=DEFAULT_KEYWORDS)


def token_tuples(lexer):
    return [(t.type, t.lexeme) for t in lexer.tokens]


# ---------------------------------------------------------------------------
# New keywords
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("word", ["float", "char", "while"])
def test_new_reserved_words_are_keywords(word):
    lexer = make_lexer()
    lexer.tokenize(word)
    assert token_tuples(lexer) == [("KEYWORD", word)]


def test_resource_file_matches_default_keywords():
    lexer = Lexer(keywords_path=KEYWORDS_FILE)
    assert lexer.keywords == DEFAULT_KEYWORDS


def test_keyword_prefix_is_still_an_identifier():
    lexer = make_lexer()
    lexer.tokenize("floats character whileLoop")
    assert token_tuples(lexer) == [
        ("IDENTIFIER", "floats"),
        ("IDENTIFIER", "character"),
        ("IDENTIFIER", "whileLoop"),
    ]


def test_main_is_an_identifier():
    # In C, main is a function name, not a reserved word.
    lexer = make_lexer()
    lexer.tokenize("int main ( )")
    assert token_tuples(lexer)[1] == ("IDENTIFIER", "main")


@pytest.mark.parametrize("operator", ["%", "!"])
def test_modulo_and_logical_not_are_operators(operator):
    lexer = make_lexer()
    lexer.tokenize(f"a {operator} b")
    assert token_tuples(lexer)[1] == ("OPERATOR", operator)
    assert lexer.errors == []


def test_not_equal_is_still_one_operator():
    lexer = make_lexer()
    lexer.tokenize("!a != !b")
    assert token_tuples(lexer) == [
        ("OPERATOR", "!"),
        ("IDENTIFIER", "a"),
        ("OPERATOR", "!="),
        ("OPERATOR", "!"),
        ("IDENTIFIER", "b"),
    ]


def test_while_statement():
    lexer = make_lexer()
    lexer.tokenize("while (x < 10) { x = x + 1; }")
    assert token_tuples(lexer) == [
        ("KEYWORD", "while"),
        ("PUNCTUATION", "("),
        ("IDENTIFIER", "x"),
        ("OPERATOR", "<"),
        ("CONSTANT", "10"),
        ("PUNCTUATION", ")"),
        ("PUNCTUATION", "{"),
        ("IDENTIFIER", "x"),
        ("OPERATOR", "="),
        ("IDENTIFIER", "x"),
        ("OPERATOR", "+"),
        ("CONSTANT", "1"),
        ("PUNCTUATION", ";"),
        ("PUNCTUATION", "}"),
    ]
    assert lexer.errors == []


# ---------------------------------------------------------------------------
# Character literals
# ---------------------------------------------------------------------------

def test_char_declaration():
    lexer = make_lexer()
    lexer.tokenize("char c = 'a';")
    assert token_tuples(lexer) == [
        ("KEYWORD", "char"),
        ("IDENTIFIER", "c"),
        ("OPERATOR", "="),
        ("LITERAL", "'a'"),
        ("PUNCTUATION", ";"),
    ]
    assert lexer.errors == []


@pytest.mark.parametrize(
    "literal",
    ["'a'", "'Z'", "'7'", "' '", "';'", "'\"'",
     r"'\n'", r"'\t'", r"'\r'", r"'\0'", r"'\\'", r"'\''", r"'\"'"],
)
def test_valid_char_literals(literal):
    lexer = make_lexer()
    lexer.tokenize(literal)
    assert token_tuples(lexer) == [("LITERAL", literal)]
    assert lexer.errors == []


def test_char_literal_column_tracking():
    lexer = make_lexer()
    lexer.tokenize(r"c = '\n'; d")
    assert [(t.lexeme, t.column) for t in lexer.tokens] == [
        ("c", 1), ("=", 3), (r"'\n'", 5), (";", 9), ("d", 11),
    ]


@pytest.mark.parametrize(
    "source, error",
    [
        ("''", "''"),             # empty
        ("'ab'", "'ab'"),         # more than one character
        (r"'\q'", r"'\q'"),       # unknown escape
    ],
)
def test_malformed_char_literal_is_a_single_error(source, error):
    lexer = make_lexer()
    lexer.tokenize(source)
    assert lexer.tokens == []
    assert [e.lexeme for e in lexer.errors] == [error]


def test_malformed_char_literal_does_not_swallow_the_rest_of_the_line():
    lexer = make_lexer()
    lexer.tokenize("c = 'ab'; x")
    assert token_tuples(lexer) == [
        ("IDENTIFIER", "c"),
        ("OPERATOR", "="),
        ("PUNCTUATION", ";"),
        ("IDENTIFIER", "x"),
    ]
    assert [e.lexeme for e in lexer.errors] == ["'ab'"]


def test_unterminated_char_literal_stops_at_newline():
    lexer = make_lexer()
    lexer.tokenize("c = 'a;\nint x;")
    assert [e.lexeme for e in lexer.errors] == ["'a;"]
    assert lexer.errors[0].line == 1
    assert token_tuples(lexer) == [
        ("IDENTIFIER", "c"),
        ("OPERATOR", "="),
        ("KEYWORD", "int"),
        ("IDENTIFIER", "x"),
        ("PUNCTUATION", ";"),
    ]


def test_apostrophe_inside_string_is_not_a_char_literal():
    lexer = make_lexer()
    lexer.tokenize('"it\'s"')
    assert token_tuples(lexer) == [("LITERAL", '"it\'s"')]
    assert lexer.errors == []


def test_malformed_char_literals_are_not_counted_as_tokens():
    lexer = make_lexer()
    lexer.tokenize("char c = 'ab';")
    assert lexer.get_total_tokens() == 4

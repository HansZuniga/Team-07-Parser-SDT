from lexer import Lexer, DEFAULT_KEYWORDS


def make_lexer():
    return Lexer(keywords=DEFAULT_KEYWORDS)


def token_tuples(lexer):
    return [(t.type, t.lexeme) for t in lexer.tokens]


# ---------------------------------------------------------------------------
# Professor's reading example (docs/Lexer.pdf)
# ---------------------------------------------------------------------------

def test_printf_line_produces_five_tokens():
    lexer = make_lexer()
    lexer.tokenize('printf("This is an example");')

    assert token_tuples(lexer) == [
        ("IDENTIFIER", "printf"),
        ("PUNCTUATION", "("),
        ("LITERAL", '"This is an example"'),
        ("PUNCTUATION", ")"),
        ("PUNCTUATION", ";"),
    ]
    assert lexer.get_total_tokens() == 5
    assert lexer.errors == []


def test_int_declaration_produces_five_tokens():
    lexer = make_lexer()
    lexer.tokenize("int a = 10;")

    assert token_tuples(lexer) == [
        ("KEYWORD", "int"),
        ("IDENTIFIER", "a"),
        ("OPERATOR", "="),
        ("CONSTANT", "10"),
        ("PUNCTUATION", ";"),
    ]
    assert lexer.get_total_tokens() == 5


def test_both_professor_lines_produce_ten_tokens():
    lexer = make_lexer()
    source = 'printf("This is an example");\nint a = 10;'
    lexer.tokenize(source)

    assert lexer.get_total_tokens() == 10
    assert lexer.errors == []


# ---------------------------------------------------------------------------
# Keywords vs identifiers (docs/Especificacion_Tokens.pdf, section 3 and 4)
# ---------------------------------------------------------------------------

def test_reserved_word_is_keyword():
    lexer = make_lexer()
    lexer.tokenize("if")
    assert token_tuples(lexer) == [("KEYWORD", "if")]


def test_identifier_with_reserved_prefix_is_not_split():
    lexer = make_lexer()
    lexer.tokenize("if2")
    assert token_tuples(lexer) == [("IDENTIFIER", "if2")]


def test_intx_is_a_single_identifier():
    lexer = make_lexer()
    lexer.tokenize("intx")
    assert token_tuples(lexer) == [("IDENTIFIER", "intx")]


def test_printf_is_identifier_not_keyword():
    lexer = make_lexer()
    lexer.tokenize("printf")
    assert token_tuples(lexer) == [("IDENTIFIER", "printf")]


# ---------------------------------------------------------------------------
# Operators and separators (docs/Especificacion_Tokens.pdf, section 4)
# ---------------------------------------------------------------------------

def test_a_minus_b_is_three_tokens():
    lexer = make_lexer()
    lexer.tokenize("a-b")
    assert token_tuples(lexer) == [
        ("IDENTIFIER", "a"),
        ("OPERATOR", "-"),
        ("IDENTIFIER", "b"),
    ]


def test_two_character_operators_are_not_split():
    lexer = make_lexer()
    lexer.tokenize(">= <= == !=")
    assert token_tuples(lexer) == [
        ("OPERATOR", ">="),
        ("OPERATOR", "<="),
        ("OPERATOR", "=="),
        ("OPERATOR", "!="),
    ]


def test_signed_constant_is_operator_and_constant():
    lexer = make_lexer()
    lexer.tokenize("-10")
    assert token_tuples(lexer) == [
        ("OPERATOR", "-"),
        ("CONSTANT", "10"),
    ]


# ---------------------------------------------------------------------------
# Numeric constants and malformed numeric candidates (section 5)
# ---------------------------------------------------------------------------

def test_decimal_constant():
    lexer = make_lexer()
    lexer.tokenize("3.14")
    assert token_tuples(lexer) == [("CONSTANT", "3.14")]
    assert lexer.errors == []


def test_malformed_123abc_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("123abc")
    assert lexer.tokens == []
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == "123abc"


def test_malformed_trailing_dot_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("3.")
    assert lexer.tokens == []
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == "3."


def test_malformed_double_dot_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("1.2.3")
    assert lexer.tokens == []
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == "1.2.3"


def test_identifier_starting_with_digit_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("2a")
    assert lexer.tokens == []
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == "2a"


# ---------------------------------------------------------------------------
# String literals (section 5)
# ---------------------------------------------------------------------------

def test_empty_string_literal():
    lexer = make_lexer()
    lexer.tokenize('""')
    assert token_tuples(lexer) == [("LITERAL", '""')]


def test_unterminated_string_is_reported_as_error():
    lexer = make_lexer()
    lexer.tokenize('"unterminated')
    assert lexer.tokens == []
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == '"unterminated'


def test_unterminated_string_stops_at_newline():
    lexer = make_lexer()
    lexer.tokenize('"unterminated\nint a;')
    assert len(lexer.errors) == 1
    assert lexer.errors[0].lexeme == '"unterminated'
    # Scanning continues normally on the next line.
    assert token_tuples(lexer) == [
        ("KEYWORD", "int"),
        ("IDENTIFIER", "a"),
        ("PUNCTUATION", ";"),
    ]


# ---------------------------------------------------------------------------
# Illegal / undefined characters (section 3 and 5)
# ---------------------------------------------------------------------------

def test_undefined_operator_characters_are_errors():
    lexer = make_lexer()
    lexer.tokenize("a & b ! c")
    error_lexemes = [e.lexeme for e in lexer.errors]
    assert error_lexemes == ["&", "!"]


def test_undefined_bracket_characters_are_errors():
    lexer = make_lexer()
    lexer.tokenize("[ ]")
    error_lexemes = [e.lexeme for e in lexer.errors]
    assert error_lexemes == ["[", "]"]


def test_illegal_character_advances_a_single_position():
    lexer = make_lexer()
    lexer.tokenize("a @ b")
    assert token_tuples(lexer) == [
        ("IDENTIFIER", "a"),
        ("IDENTIFIER", "b"),
    ]
    assert [e.lexeme for e in lexer.errors] == ["@"]


def test_non_ascii_letter_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("int á = 10;")
    assert token_tuples(lexer) == [
        ("KEYWORD", "int"),
        ("OPERATOR", "="),
        ("CONSTANT", "10"),
        ("PUNCTUATION", ";"),
    ]
    assert [(e.lexeme, e.line, e.column) for e in lexer.errors] == [("á", 1, 5)]


def test_non_ascii_digit_is_a_single_error():
    lexer = make_lexer()
    lexer.tokenize("a = ²;")
    assert [e.lexeme for e in lexer.errors] == ["²"]
    assert lexer.get_total_tokens() == 3


# ---------------------------------------------------------------------------
# Line and column tracking
# ---------------------------------------------------------------------------

def test_line_and_column_are_tracked_across_lines():
    lexer = make_lexer()
    lexer.tokenize("int a;\nint b;")

    positions = [(t.type, t.lexeme, t.line, t.column) for t in lexer.tokens]
    assert positions == [
        ("KEYWORD", "int", 1, 1),
        ("IDENTIFIER", "a", 1, 5),
        ("PUNCTUATION", ";", 1, 6),
        ("KEYWORD", "int", 2, 1),
        ("IDENTIFIER", "b", 2, 5),
        ("PUNCTUATION", ";", 2, 6),
    ]


def test_tab_advances_column_by_one():
    lexer = make_lexer()
    lexer.tokenize("\ta")
    assert lexer.tokens[0].line == 1
    assert lexer.tokens[0].column == 2


# ---------------------------------------------------------------------------
# Whitespace-only / empty input
# ---------------------------------------------------------------------------

def test_empty_input_produces_no_tokens():
    lexer = make_lexer()
    lexer.tokenize("")
    assert lexer.tokens == []
    assert lexer.errors == []
    assert lexer.get_total_tokens() == 0


def test_whitespace_only_input_produces_no_tokens():
    lexer = make_lexer()
    lexer.tokenize("   \t  \n  \n")
    assert lexer.tokens == []
    assert lexer.errors == []


# ---------------------------------------------------------------------------
# Loading keywords from a resource file
# ---------------------------------------------------------------------------

def test_keywords_loaded_from_resource_file(tmp_path):
    keywords_file = tmp_path / "keywords.txt"
    keywords_file.write_text("foo\nbar\n", encoding="utf-8")

    lexer = Lexer(keywords_path=keywords_file)
    lexer.tokenize("foo baz")

    assert token_tuples(lexer) == [
        ("KEYWORD", "foo"),
        ("IDENTIFIER", "baz"),
    ]


# ---------------------------------------------------------------------------
# Byte-order mark (BOM) handling in source files
#
# Found while running manual experiments: a file saved with Windows Notepad
# (or PowerShell's `Out-File -Encoding utf8`) can start with a UTF-8 BOM
# (U+FEFF). Opening such a file as plain "utf-8" leaves that character in
# the text, and the lexer used to report it as an illegal character. Fixed
# by reading source and resource files with "utf-8-sig".
# ---------------------------------------------------------------------------

def test_tokenize_file_strips_leading_bom(tmp_path):
    source_file = tmp_path / "with_bom.c"
    source_file.write_bytes(b"\xef\xbb\xbfint a = 10;")

    lexer = make_lexer()
    lexer.tokenize_file(source_file)

    assert token_tuples(lexer) == [
        ("KEYWORD", "int"),
        ("IDENTIFIER", "a"),
        ("OPERATOR", "="),
        ("CONSTANT", "10"),
        ("PUNCTUATION", ";"),
    ]
    assert lexer.errors == []

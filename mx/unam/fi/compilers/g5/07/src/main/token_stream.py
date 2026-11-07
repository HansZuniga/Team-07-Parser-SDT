"""
Authors:
    Team 07:
    - Arzate Rios Adrian Axel
    - Bojorquez Covarrubias Evans Martin
    - Parra Bello Carlos Enrique
    - Yanez Barajas Brandon
    - Zuniga Garcia Hans David

Program description:
Bridge between the lexical analyzer and the CLR(1) parser (issue #7).

The lexer classifies lexemes into broad categories (KEYWORD, IDENTIFIER,
CONSTANT, ...), while the ACTION/GOTO table is indexed by the terminal
symbols of the grammar (int, id, num, =, ;, $, ...). This module:

1. Runs the existing lexer (no lexical analysis is duplicated here).
2. Stops if the lexer reported any lexical error, so an invalid token
   stream never reaches the parser.
3. Maps every lexer token to its grammar terminal.
4. Appends the end-of-input terminal `$`.

Each resulting `Terminal` keeps the original token, so the parser and the
SDT module still have the lexeme, line and column for error messages and
semantic attributes.

Token -> terminal mapping
-------------------------
    KEYWORD      'int'      ->  int        (the keyword itself)
    IDENTIFIER   'x'        ->  id
    CONSTANT     '10'       ->  num        (integer and decimal constants)
    LITERAL      'a'        ->  char_lit   (character literal)
    LITERAL      "hi"       ->  string_lit (string literal)
    OPERATOR     '='        ->  =          (the operator itself)
    PUNCTUATION  ';'        ->  ;          (the punctuation itself)
    (end of input)          ->  $

The names id, num, char_lit and string_lit are placeholders until the final
grammar (issue #2) fixes the terminal names; they are defined only in the
constants below, so renaming them is a one-line change.
"""

from pathlib import Path

from lexer import Lexer

RESOURCES_DIR = Path(__file__).resolve().parents[2] / "resources"
KEYWORDS_PATH = RESOURCES_DIR / "keywords.txt"

# Grammar terminal names for the token categories whose lexeme varies.
IDENTIFIER_TERMINAL = "id"
CONSTANT_TERMINAL = "num"
CHAR_LITERAL_TERMINAL = "char_lit"
STRING_LITERAL_TERMINAL = "string_lit"
END_OF_INPUT = "$"

# Categories whose terminal is the lexeme itself (int, while, +, ==, ;, {).
_LEXEME_IS_TERMINAL = {"KEYWORD", "OPERATOR", "PUNCTUATION"}


class Terminal:
    """
    One grammar terminal of the parser's input, plus the lexer token it
    came from. `token` is None only for the end-of-input terminal `$`.
    """

    __slots__ = ("symbol", "token", "line", "column")

    def __init__(self, symbol, token, line, column):
        self.symbol = symbol
        self.token = token
        self.line = line
        self.column = column

    @property
    def lexeme(self):
        return self.token.lexeme if self.token is not None else END_OF_INPUT

    def __repr__(self):
        return (
            f"Terminal({self.symbol!r}, lexeme={self.lexeme!r}, "
            f"line={self.line}, column={self.column})"
        )


class LexicalError(Exception):
    """
    Raised when the source has lexical errors. Parsing must not start.
    `errors` holds every error token the lexer reported, in source order.
    """

    def __init__(self, errors):
        self.errors = list(errors)
        first = self.errors[0]
        super().__init__(f"Lexical error in line {first.line}")

    @property
    def line(self):
        return self.errors[0].line


def to_terminal(token):
    """Return the grammar terminal symbol for a single lexer token."""
    if token.type in _LEXEME_IS_TERMINAL:
        return token.lexeme
    if token.type == "IDENTIFIER":
        return IDENTIFIER_TERMINAL
    if token.type == "CONSTANT":
        return CONSTANT_TERMINAL
    if token.type == "LITERAL":
        if token.lexeme.startswith("'"):
            return CHAR_LITERAL_TERMINAL
        return STRING_LITERAL_TERMINAL
    raise ValueError(f"Token type without a grammar terminal: {token.type!r}")


def _end_of_input(tokens):
    """
    Build `$`. It is placed right after the last token, so a parser error
    such as a missing ';' at the end of the file reports the line where the
    program actually ends.
    """
    if not tokens:
        return Terminal(END_OF_INPUT, None, 1, 1)
    last = tokens[-1]
    return Terminal(END_OF_INPUT, None, last.line, last.column + len(last.lexeme))


def build_terminals(tokens, errors=()):
    """
    Turn the lexer's output into the parser input, ending with `$`.

    Raises LexicalError if `errors` is not empty.
    """
    if errors:
        raise LexicalError(errors)
    terminals = [
        Terminal(to_terminal(token), token, token.line, token.column)
        for token in tokens
    ]
    terminals.append(_end_of_input(tokens))
    return terminals


def _new_lexer():
    return Lexer(keywords_path=KEYWORDS_PATH)


def tokenize_source(text, lexer=None):
    """Run the lexer over `text` and return the parser's terminal list."""
    lexer = lexer or _new_lexer()
    tokens = lexer.tokenize(text)
    return build_terminals(tokens, lexer.errors)


def tokenize_file(file_path, lexer=None):
    """Run the lexer over a source file and return the terminal list."""
    lexer = lexer or _new_lexer()
    tokens = lexer.tokenize_file(file_path)
    return build_terminals(tokens, lexer.errors)

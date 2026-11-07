r"""
Authors:
    Team 07:
    - Arzate Rios Adrian Axel
    - Bojorquez Covarrubias Evans Martin
    - Parra Bello Carlos Enrique
    - Yanez Barajas Brandon
    - Zuniga Garcia Hans David

Program description:
The Lexer class performs lexical analysis over a string or a source file,
scanning it from left to right and classifying each lexeme into one of the
token categories defined for this project.

Token Categories:
- KEYWORD
- IDENTIFIER
- OPERATOR
- CONSTANT
- LITERAL
- PUNCTUATION

Design reference:
This implementation follows the team's "Especificacion de tokens y
expresiones regulares" document (docs/Especificacion_Tokens.pdf):

    KEYWORD      (?:print|int|return|if|else)
    IDENTIFIER   [A-Za-z_][A-Za-z0-9_]*
    CONSTANT     [0-9]+(?:\.[0-9]+)?
    LITERAL      "[^"\r\n]*"
    OPERATOR     ==|!=|<=|>=|[=+*/<>-]
    PUNCTUATION  [(){};,]

Whitespace (spaces, tabs) and newlines are not reported as tokens, but they
update the current line/column position. Every character, including a tab,
advances the column by one; a newline resets the column to 1 and advances
the line by one.

Error handling:
- A malformed numeric candidate (a digit followed by letters, underscores
  or dots) is consumed as a whole and reported as a single lexical error
  if it does not match the CONSTANT pattern exactly (e.g. "123abc", "3.",
  "1.2.3"). It is never split into partially valid tokens.
- An unterminated string literal is consumed up to the next newline or the
  end of the input and reported as a single lexical error.
- Any other unrecognized character is reported as a one-character lexical
  error and the scan advances a single position.
- Lexical errors are not included in the total count of valid tokens.
"""

import re
from pathlib import Path

# Default reserved words, used when no keywords.txt resource is supplied.
DEFAULT_KEYWORDS = {"print", "int", "return", "if", "else"}

# A malformed numeric candidate: starts with a digit and may continue with
# digits, letters, underscores or dots. Used to capture ill-formed numeric
# lexemes (such as "123abc" or "1.2.3") as a single error token instead of
# splitting them into several (partially) valid tokens.
_NUMERIC_CANDIDATE_RE = re.compile(r"[0-9][0-9A-Za-z_.]*")

# Token patterns, applied at the current scanning position.
_CONSTANT_RE = re.compile(r"[0-9]+(?:\.[0-9]+)?")
_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LITERAL_RE = re.compile(r'"[^"\r\n]*"')
_OPERATOR_RE = re.compile(r"==|!=|<=|>=|[=+*/<>-]")
_PUNCTUATION_RE = re.compile(r"[(){};,]")


class Token:
    """A single recognized lexeme with its category and source position."""

    __slots__ = ("type", "lexeme", "line", "column")

    def __init__(self, token_type, lexeme, line, column):
        self.type = token_type
        self.lexeme = lexeme
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token({self.type!r}, {self.lexeme!r}, "
            f"line={self.line}, column={self.column})"
        )

    def as_dict(self):
        return {
            "type": self.type,
            "lexeme": self.lexeme,
            "line": self.line,
            "column": self.column,
        }


class Lexer:
    """
    Lexer performs lexical analysis over a string or a source file.

    Parameters
    ----------
    keywords : iterable, optional
        An explicit set of reserved words. Ignored if `keywords_path` is
        given.
    keywords_path : str or Path, optional
        Path to a text file with one reserved word per line. If the file
        does not exist, the lexer falls back to DEFAULT_KEYWORDS.
    """

    def __init__(self, keywords=None, keywords_path=None):
        if keywords_path is not None:
            self.keywords = self._load_keywords(keywords_path)
        elif keywords is not None:
            self.keywords = set(keywords)
        else:
            self.keywords = set(DEFAULT_KEYWORDS)

        self.tokens = []
        self.errors = []
        self.total_tokens = 0

    @staticmethod
    def _load_keywords(path):
        path = Path(path)
        words = set()
        if path.exists():
            # "utf-8-sig" transparently strips a leading BOM (U+FEFF) if the
            # file has one (common when a file is saved with Windows
            # Notepad), without affecting plain UTF-8 files.
            with open(path, "r", encoding="utf-8-sig") as file:
                for line in file:
                    word = line.strip()
                    if word:
                        words.add(word)
        return words if words else set(DEFAULT_KEYWORDS)

    def reset(self):
        """Clear all stored tokens, errors and counters."""
        self.tokens = []
        self.errors = []
        self.total_tokens = 0

    def tokenize_file(self, file_path):
        """Read a source file and tokenize its contents."""
        # "utf-8-sig" transparently strips a leading BOM (U+FEFF) if the
        # file has one (common when a file is saved with Windows Notepad),
        # without affecting plain UTF-8 files that have no BOM.
        with open(file_path, "r", encoding="utf-8-sig") as file:
            text = file.read()
        return self.tokenize(text)

    def tokenize(self, text):
        """
        Scan `text` from left to right and classify every lexeme found.

        Returns the list of recognized Token objects. Lexical errors are
        collected separately in `self.errors` and are not counted towards
        `self.total_tokens`.
        """
        self.reset()

        pos = 0
        line = 1
        column = 1
        length = len(text)

        while pos < length:
            char = text[pos]

            # Newlines: reset column, advance line.
            if char == "\n":
                pos += 1
                line += 1
                column = 1
                continue

            # Whitespace: does not generate a token, updates position.
            if char in (" ", "\t"):
                pos += 1
                column += 1
                continue

            # String literals.
            if char == '"':
                match = _LITERAL_RE.match(text, pos)
                if match:
                    lexeme = match.group()
                    self._add_token("LITERAL", lexeme, line, column)
                else:
                    # Unterminated string: consume up to end of line/input.
                    end = text.find("\n", pos)
                    if end == -1:
                        end = length
                    lexeme = text[pos:end]
                    self._add_error(lexeme, line, column)
                pos, column = self._advance(pos, column, len(lexeme))
                continue

            # Identifiers and keywords. The pattern itself decides whether an
            # identifier starts here: str.isalpha() also accepts non-ASCII
            # letters (e.g. "á") that the IDENTIFIER pattern does not allow.
            match = _IDENTIFIER_RE.match(text, pos)
            if match:
                lexeme = match.group()
                token_type = "KEYWORD" if lexeme in self.keywords else "IDENTIFIER"
                self._add_token(token_type, lexeme, line, column)
                pos, column = self._advance(pos, column, len(lexeme))
                continue

            # Numeric constants (and malformed numeric candidates).
            match = _NUMERIC_CANDIDATE_RE.match(text, pos)
            if match:
                candidate = match.group()
                if _CONSTANT_RE.fullmatch(candidate):
                    self._add_token("CONSTANT", candidate, line, column)
                else:
                    self._add_error(candidate, line, column)
                pos, column = self._advance(pos, column, len(candidate))
                continue

            # Operators (two-character operators are tried first).
            match = _OPERATOR_RE.match(text, pos)
            if match:
                lexeme = match.group()
                self._add_token("OPERATOR", lexeme, line, column)
                pos, column = self._advance(pos, column, len(lexeme))
                continue

            # Punctuation.
            match = _PUNCTUATION_RE.match(text, pos)
            if match:
                lexeme = match.group()
                self._add_token("PUNCTUATION", lexeme, line, column)
                pos, column = self._advance(pos, column, len(lexeme))
                continue

            # Illegal character: register and advance a single position.
            self._add_error(char, line, column)
            pos, column = self._advance(pos, column, 1)

        return self.tokens

    @staticmethod
    def _advance(pos, column, consumed):
        return pos + consumed, column + consumed

    def _add_token(self, token_type, lexeme, line, column):
        self.tokens.append(Token(token_type, lexeme, line, column))
        self.total_tokens += 1

    def _add_error(self, lexeme, line, column):
        self.errors.append(Token("ERROR", lexeme, line, column))

    def get_total_tokens(self):
        """Return the total count of recognized valid tokens."""
        return self.total_tokens

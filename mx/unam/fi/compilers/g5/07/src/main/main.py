"""
Entry point for the Team 07 lexical analyzer.

Usage
-----
Analyze a source file:

    python main.py --file ../../examples/example_profesor.c

Analyze a literal string:

    python main.py --text 'int a = 10;'

Show the terminal sequence the CLR(1) parser will receive:

    python main.py --text 'int a = 10;' --terminals

With no arguments, it runs the professor's reading example:

    printf("This is an example");
    int a = 10;
"""

import argparse
from pathlib import Path

from lexer import Lexer
from token_stream import LexicalError, build_terminals

RESOURCES_DIR = Path(__file__).resolve().parents[2] / "resources"
DEFAULT_EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "example_profesor.c"


def print_report(lexer: Lexer) -> None:
    print(f"{'TYPE':<12} {'LEXEME':<25} {'LINE':<6} {'COLUMN':<6}")
    print("-" * 52)
    for token in lexer.tokens:
        print(f"{token.type:<12} {token.lexeme!r:<25} {token.line:<6} {token.column:<6}")

    if lexer.errors:
        print()
        print("Lexical errors:")
        print(f"{'LEXEME':<25} {'LINE':<6} {'COLUMN':<6}")
        print("-" * 40)
        for error in lexer.errors:
            print(f"{error.lexeme!r:<25} {error.line:<6} {error.column:<6}")

    print()
    print(f"Total of tokens: {lexer.get_total_tokens()}")
    if lexer.errors:
        print(f"Total of lexical errors: {len(lexer.errors)}")


def print_terminals(lexer: Lexer) -> None:
    try:
        terminals = build_terminals(lexer.tokens, lexer.errors)
    except LexicalError as error:
        print(error)
        return

    print(f"{'TERMINAL':<12} {'LEXEME':<25} {'LINE':<6} {'COLUMN':<6}")
    print("-" * 52)
    for terminal in terminals:
        print(
            f"{terminal.symbol:<12} {terminal.lexeme!r:<25} "
            f"{terminal.line:<6} {terminal.column:<6}"
        )
    print()
    print("Parser input: " + " ".join(t.symbol for t in terminals))


def main() -> None:
    parser = argparse.ArgumentParser(description="Team 07 lexical analyzer")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="path to a source file to scan")
    group.add_argument("--text", help="literal source text to scan")
    parser.add_argument(
        "--terminals",
        action="store_true",
        help="show the grammar terminals sent to the parser instead of the tokens",
    )
    args = parser.parse_args()

    keywords_path = RESOURCES_DIR / "keywords.txt"
    lexer = Lexer(keywords_path=keywords_path)

    if args.file:
        lexer.tokenize_file(args.file)
    elif args.text:
        lexer.tokenize(args.text)
    else:
        lexer.tokenize_file(DEFAULT_EXAMPLE)

    if args.terminals:
        print_terminals(lexer)
    else:
        print_report(lexer)


if __name__ == "__main__":
    main()

"""
Entry point for the Team 07 lexical analyzer and CLR(1) parser.

Usage
-----
Analyze a source file:

    python main.py --file ../../examples/example_profesor.c

Analyze a literal string:

    python main.py --text 'int a = 10;'

Show the terminal sequence the CLR(1) parser will receive:

    python main.py --text 'int a = 10;' --terminals

Parse a program with the CLR(1) parser (Parsing Success! / Parsing error
in line n / Lexical error in line n):

    python main.py --file program.c --parse

Also show every parser step, or the parse tree:

    python main.py --file program.c --trace
    python main.py --file program.c --tree

With no arguments, it runs the professor's reading example:

    printf("This is an example");
    int a = 10;
"""

import argparse
from pathlib import Path

from lexer import Lexer
from token_stream import LexicalError, build_terminals
from clr1_parser import ParseError, Parser, TableError

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


def print_trace(steps) -> None:
    print(f"{'STEP':<6} {'STACK (states)':<28} {'INPUT':<8} ACTION")
    print("-" * 78)
    for step in steps:
        states = " ".join(str(s) for s in step.states)
        if len(states) > 27:
            states = "... " + states[-23:]
        print(f"{step.number:<6} {states:<28} {step.lookahead:<8} {step.action}")
    print()


def run_parser(lexer: Lexer, trace: bool, tree: bool) -> None:
    try:
        terminals = build_terminals(lexer.tokens, lexer.errors)
    except LexicalError as error:
        print(error)
        return

    try:
        parser = Parser()
    except TableError as error:
        print(error)
        return

    try:
        result = parser.parse(terminals, trace=trace)
    except ParseError as error:
        if trace:
            print_trace(error.steps)
            print(error.details())
        print(error)
        return

    if trace:
        print_trace(result.steps)
    if tree:
        print(result.tree.pretty())
        print()
    print(result.message)


def main() -> None:
    parser = argparse.ArgumentParser(description="Team 07 lexical analyzer and CLR(1) parser")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--file", help="path to a source file to scan")
    group.add_argument("--text", help="literal source text to scan")
    parser.add_argument(
        "--terminals",
        action="store_true",
        help="show the grammar terminals sent to the parser instead of the tokens",
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help="run the CLR(1) parser and print Parsing Success! or the error",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="run the parser and show every shift/reduce step",
    )
    parser.add_argument(
        "--tree",
        action="store_true",
        help="run the parser and show the parse tree",
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

    if args.parse or args.trace or args.tree:
        run_parser(lexer, trace=args.trace, tree=args.tree)
    elif args.terminals:
        print_terminals(lexer)
    else:
        print_report(lexer)


if __name__ == "__main__":
    main()

"""
Authors:
    Team 07:
    - Arzate Rios Adrian Axel
    - Bojorquez Covarrubias Evans Martin
    - Parra Bello Carlos Enrique
    - Yanez Barajas Brandon
    - Zuniga Garcia Hans David

Program description:
Bottom-up CLR(1) parser engine (issue #5).

The engine does not compute the LR(1) collection itself: it reads the
grammar and the ACTION/GOTO table produced by the Model Designer (issues
#2, #3 and #4) from two JSON files:

    gramatica.json    [{"id": 0, "lhs": "Start", "rhs": ["Program"]}, ...]
    action_goto.json  {"action": [{"state": 0, "terminal": "int",
                                   "actions": [["s", 2]]}, ...],
                       "goto":   [{"state": 0, "nonterminal": "Program",
                                   "target": 1}, ...]}

Actions are ["s", n] (shift and go to state n), ["r", p] (reduce by
production p) and ["acc", 0] (accept).

Parsing algorithm (standard LR driver):

    1. Look at the state on top of the stack and the current terminal.
    2. Consult ACTION[state, terminal].
    3. SHIFT  -> push the terminal and the new state, advance the input.
       REDUCE -> pop |rhs| entries, then push GOTO[exposed state, lhs].
       ACCEPT -> the whole input is a Program.
       (empty) -> syntax error in the line of the current terminal.

Every reduction builds a parse tree node, so a successful parse returns
the root of the tree (used later by the SDT, issue #8). Each step can also
be recorded as a trace for debugging and the project demo.
"""

import json
from pathlib import Path

from token_stream import END_OF_INPUT

PARSER_RESOURCES_DIR = Path(__file__).resolve().parents[2] / "resources" / "parser"
GRAMMAR_PATH = PARSER_RESOURCES_DIR / "gramatica.json"
TABLE_PATH = PARSER_RESOURCES_DIR / "action_goto.json"

SHIFT = "s"
REDUCE = "r"
ACCEPT = "acc"


# ---------------------------------------------------------------------------
# Grammar and table
# ---------------------------------------------------------------------------

class Production:
    """One grammar production `lhs -> rhs`. An empty rhs is epsilon."""

    __slots__ = ("id", "lhs", "rhs")

    def __init__(self, production_id, lhs, rhs):
        self.id = production_id
        self.lhs = lhs
        self.rhs = tuple(rhs)

    def __str__(self):
        body = " ".join(self.rhs) if self.rhs else "epsilon"
        return f"{self.lhs} -> {body}"

    def __repr__(self):
        return f"Production({self.id}, {str(self)!r})"


class TableError(Exception):
    """The grammar or the ACTION/GOTO table files are not usable."""


class ParsingTable:
    """
    The grammar productions plus the ACTION and GOTO tables.

    `action[(state, terminal)]` is a pair (kind, number) and
    `goto[(state, nonterminal)]` is the target state.
    """

    def __init__(self, productions, action, goto):
        self.productions = productions
        self.action = action
        self.goto = goto

    @classmethod
    def from_files(cls, grammar_path=GRAMMAR_PATH, table_path=TABLE_PATH):
        grammar_path, table_path = Path(grammar_path), Path(table_path)
        for path in (grammar_path, table_path):
            if not path.is_file():
                raise TableError(f"Parser resource not found: {path}")
        with open(grammar_path, encoding="utf-8-sig") as file:
            grammar = json.load(file)
        with open(table_path, encoding="utf-8-sig") as file:
            table = json.load(file)
        return cls.from_data(grammar, table)

    @classmethod
    def from_data(cls, grammar, table):
        productions = {}
        for entry in grammar:
            production = Production(entry["id"], entry["lhs"], entry["rhs"])
            productions[production.id] = production

        action = {}
        for entry in table["action"]:
            key = (entry["state"], entry["terminal"])
            actions = [tuple(a) for a in entry["actions"]]
            # A CLR(1) table for our grammar has no conflicts. If one ever
            # appears, refuse the table instead of picking an action.
            if len(actions) != 1:
                raise TableError(
                    f"Conflict in ACTION[{key[0]}, {key[1]!r}]: {actions}"
                )
            kind, number = actions[0]
            if kind not in (SHIFT, REDUCE, ACCEPT):
                raise TableError(f"Unknown action {kind!r} in ACTION{key}")
            if kind == REDUCE and number not in productions:
                raise TableError(f"ACTION{key} reduces by unknown production {number}")
            action[key] = (kind, number)

        goto = {}
        for entry in table["goto"]:
            goto[(entry["state"], entry["nonterminal"])] = entry["target"]

        return cls(productions, action, goto)

    def expected_terminals(self, state):
        """Terminals that have an action in `state`, sorted (for messages)."""
        return sorted(t for (s, t) in self.action if s == state)


# ---------------------------------------------------------------------------
# Parse tree (minimal node; issue #9 builds the readable representation)
# ---------------------------------------------------------------------------

class ParseNode:
    """
    A parse tree node.

    - Terminal node: `terminal` is the Terminal from token_stream (lexeme,
      line, column); `production` is None and there are no children.
    - Non-terminal node: `production` is the Production used in the
      reduction and `children` follow its right-hand side, left to right.
      An epsilon reduction has no children.
    """

    __slots__ = ("symbol", "children", "production", "terminal")

    def __init__(self, symbol, children=(), production=None, terminal=None):
        self.symbol = symbol
        self.children = list(children)
        self.production = production
        self.terminal = terminal

    @property
    def is_terminal(self):
        return self.terminal is not None

    @property
    def lexeme(self):
        return self.terminal.lexeme if self.terminal is not None else None

    @property
    def line(self):
        """Source line: the terminal's own line, or the first one below."""
        stack = [self]
        while stack:
            node = stack.pop()
            if node.terminal is not None:
                return node.terminal.line
            stack.extend(reversed(node.children))
        return None

    def pretty(self, indent=0):
        """
        Indented text form of the subtree, one node per line. Uses an
        explicit stack, so long programs (deep Items chains) do not hit
        Python's recursion limit.
        """
        lines = []
        stack = [(self, indent)]
        while stack:
            node, depth = stack.pop()
            pad = "  " * depth
            if node.is_terminal:
                lines.append(f"{pad}{node.symbol} {node.lexeme!r} (line {node.line})")
            elif not node.children:
                lines.append(f"{pad}{node.symbol} -> epsilon")
            else:
                lines.append(f"{pad}{node.symbol}")
            for child in reversed(node.children):
                stack.append((child, depth + 1))
        return "\n".join(lines)

    def __repr__(self):
        if self.is_terminal:
            return f"ParseNode({self.symbol!r}, lexeme={self.lexeme!r})"
        return f"ParseNode({self.symbol!r}, children={len(self.children)})"


# ---------------------------------------------------------------------------
# Errors and trace
# ---------------------------------------------------------------------------

class ParseError(Exception):
    """
    Syntax error. `line` follows the project output format
    "Parsing error in line n".
    """

    def __init__(self, line, terminal, state, expected):
        self.line = line
        self.terminal = terminal
        self.state = state
        self.expected = list(expected)
        self.steps = None          # filled when parsing with trace=True
        super().__init__(f"Parsing error in line {line}")

    def details(self):
        """Longer message for debugging: what was found and expected."""
        found = self.terminal.lexeme
        expected = ", ".join(self.expected) or "nothing"
        return (
            f"{self} (column {self.terminal.column}): unexpected {found!r} "
            f"in state {self.state}; expected one of: {expected}"
        )


class Step:
    """One row of the parser trace."""

    __slots__ = ("number", "states", "symbols", "lookahead", "action")

    def __init__(self, number, states, symbols, lookahead, action):
        self.number = number
        self.states = tuple(states)
        self.symbols = tuple(symbols)
        self.lookahead = lookahead
        self.action = action

    def __repr__(self):
        return f"Step({self.number}, lookahead={self.lookahead!r}, action={self.action!r})"


class ParseResult:
    """Outcome of a successful parse: the tree root and the trace."""

    message = "Parsing Success!"

    def __init__(self, tree, steps):
        self.tree = tree
        self.steps = steps


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class Parser:
    """
    CLR(1) parser driver.

    Usage:
        parser = Parser()                       # loads resources/parser/*.json
        result = parser.parse(tokenize_source(text))
        print(result.message)                   # Parsing Success!
    """

    def __init__(self, table=None):
        self.table = table if table is not None else ParsingTable.from_files()

    def parse(self, terminals, trace=False):
        """
        Parse a terminal list ending in `$` (see token_stream).

        Returns a ParseResult on success; raises ParseError otherwise.
        If `trace` is True, ParseResult.steps (and ParseError.steps) hold
        every action taken.
        """
        if not terminals or terminals[-1].symbol != END_OF_INPUT:
            raise ValueError("The terminal list must end with '$'")

        states = [0]          # state stack
        nodes = []            # parse tree nodes, parallel to states[1:]
        steps = [] if trace else None
        position = 0

        while True:
            state = states[-1]
            current = terminals[position]
            entry = self.table.action.get((state, current.symbol))

            if entry is None:
                error = ParseError(
                    self._error_line(terminals, position, states),
                    current,
                    state,
                    self.table.expected_terminals(state),
                )
                if trace:
                    self._record(steps, states, nodes, current, "error")
                    error.steps = steps
                raise error

            kind, number = entry

            if kind == SHIFT:
                if trace:
                    self._record(steps, states, nodes, current, f"shift {number}")
                states.append(number)
                nodes.append(ParseNode(current.symbol, terminal=current))
                position += 1

            elif kind == REDUCE:
                production = self.table.productions[number]
                size = len(production.rhs)
                exposed = states[-1 - size]   # state left after popping |rhs|
                target = self.table.goto.get((exposed, production.lhs))
                if target is None:
                    # Only possible with an inconsistent table.
                    raise TableError(
                        f"Missing GOTO[{exposed}, {production.lhs!r}] "
                        f"after reducing by production {production.id}"
                    )
                if trace:
                    self._record(
                        steps, states, nodes, current,
                        f"reduce {production.id} ({production}), goto {target}",
                    )
                children = nodes[len(nodes) - size:] if size else []
                if size:
                    del states[-size:]
                    del nodes[-size:]
                states.append(target)
                nodes.append(ParseNode(production.lhs, children, production))

            else:  # ACCEPT
                if trace:
                    self._record(steps, states, nodes, current, "accept")
                return ParseResult(nodes[-1], steps)

    def _error_line(self, terminals, position, states):
        """
        Line to report for a syntax error.

        An LR parser notices a missing ';' only when it reads the next
        terminal, which is often on the following line:

            int x = 5        <- line 2: the ';' is missing here
            return x;        <- line 3: the parser fails on 'return'

        To tell "a ';' is missing" apart from "this terminal is wrong", the
        parser tries inserting a ';' before the unexpected terminal. If the
        ';' is accepted and the unexpected terminal can follow it, the ';'
        was missing and the error belongs to the previous terminal's line
        ("Parsing error in line 2"). Otherwise the error is reported on the
        line of the unexpected terminal.
        """
        current = terminals[position]
        if position == 0:
            return current.line
        previous = terminals[position - 1]
        if current.line > previous.line:
            after_semicolon = self._shift_preview(states, ";")
            if after_semicolon is not None and (
                self._shift_preview(after_semicolon, current.symbol) is not None
            ):
                return previous.line
        return current.line

    def _shift_preview(self, states, symbol):
        """
        Simulate reading `symbol` from the state stack `states` (only the
        states matter for this). Returns the stack after the symbol is
        shifted or accepted, or None if `symbol` causes an error.
        """
        states = list(states)
        while True:
            entry = self.table.action.get((states[-1], symbol))
            if entry is None:
                return None
            kind, number = entry
            if kind == SHIFT:
                return states + [number]
            if kind == ACCEPT:
                return states
            production = self.table.productions[number]
            if production.rhs:
                del states[-len(production.rhs):]
            target = self.table.goto.get((states[-1], production.lhs))
            if target is None:
                return None
            states.append(target)

    @staticmethod
    def _record(steps, states, nodes, current, action):
        """Store the stack (before the action) and the action taken."""
        steps.append(Step(
            len(steps) + 1,
            states,
            [node.symbol for node in nodes],
            current.symbol,
            action,
        ))

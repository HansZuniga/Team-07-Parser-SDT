"""
Authors:
    Team 07:
    - Arzate Rios Adrian Axel
    - Bojorquez Covarrubias Evans Martin
    - Parra Bello Carlos Enrique
    - Yanez Barajas Brandon
    - Zuniga Garcia Hans David

Program description:
Syntax-Directed Translation / semantic analysis (issue #8).

Runs after the CLR(1) parser accepts the program. It walks the parse tree
and applies, at every node, the semantic action of the production that
built it (team document "4. Reglas SDT y tabla de simbolos"). It checks
names and types only; it never runs the program.

Type policy
-----------
- Literals: INT -> int, FLOAT -> float, CHAR -> char, STRING -> string.
- Declarable types: int, float, char. Numeric types: char, int, float.
- Initialization, assignment and return accept identity or widening
  char -> int -> float; narrowing and strings are rejected:

      destination \\ source   char  int  float
      char                    yes   no   no
      int                     yes   yes  no
      float                   yes   yes  yes

- + - * / need numbers; char is promoted to int; float if any operand is
  float, int otherwise. % needs char/int and gives int.
- Comparisons (== != < <= > >=) and ! need numbers and give int.
- Unary + and - need a number and give the promoted type.
- if/while conditions must be numeric; return must be assignable to int.

Error codes (the first error found is reported)
-----------------------------------------------
    SEM001  duplicate declaration in the same scope
    SEM002  undeclared identifier
    SEM003  incompatible assignment            (x = expr;)
    SEM004  incompatible initialization        (type x = expr;)
    SEM005  invalid operand type for an operator
    SEM006  non-numeric condition in if/while
    SEM007  return value not compatible with int

SEM001-SEM004 come from the team document; SEM005-SEM007 name the other
checks the document requires.

Scopes
------
Every Block opens a new scope; the block of main is scope 0. Lookups go
from the innermost open scope outwards. A name may be declared again in
an inner scope (shadowing), not twice in the same one. Records of closed
scopes are kept so the full symbol table can be shown at the end.
"""

INT = "int"
FLOAT = "float"
CHAR = "char"
STRING = "string"

DECLARABLE_TYPES = (CHAR, INT, FLOAT)
NUMERIC_TYPES = frozenset(DECLARABLE_TYPES)
INTEGRAL_TYPES = frozenset((CHAR, INT))
MAIN_RETURN_TYPE = INT

# Widening order: a value can be stored in a type of equal or higher rank.
_RANK = {CHAR: 0, INT: 1, FLOAT: 2}

_LITERAL_TYPES = {"INT": INT, "FLOAT": FLOAT, "CHAR": CHAR, "STRING": STRING}


def assignable(destination, source):
    """True if a value of type `source` can be stored in `destination`."""
    return (
        destination in _RANK
        and source in _RANK
        and _RANK[source] <= _RANK[destination]
    )


def promote(data_type):
    """Arithmetic promotion: char becomes int; int and float stay."""
    return INT if data_type == CHAR else data_type


# ---------------------------------------------------------------------------
# Symbol table
# ---------------------------------------------------------------------------

class Symbol:
    """One declared variable."""

    __slots__ = (
        "name", "data_type", "scope_id", "line", "column",
        "has_initializer", "initializer_type", "initializer_lexeme",
    )

    def __init__(self, name, data_type, scope_id, line, column):
        self.name = name
        self.data_type = data_type
        self.scope_id = scope_id
        self.line = line
        self.column = column
        self.has_initializer = False
        self.initializer_type = None
        self.initializer_lexeme = None

    def __repr__(self):
        return (
            f"Symbol({self.name!r}, {self.data_type}, scope={self.scope_id}, "
            f"line={self.line})"
        )


class SymbolTable:
    """
    Stack of open scopes plus the list of every symbol ever declared.

    `records` keeps declaration order and survives scope closing, so the
    final table can be printed after the analysis.
    """

    def __init__(self):
        self._open = []        # list of (scope_id, {name: Symbol})
        self._next_scope = 0
        self.records = []

    @property
    def current_scope(self):
        return self._open[-1][0]

    def open_scope(self):
        scope_id = self._next_scope
        self._next_scope += 1
        self._open.append((scope_id, {}))
        return scope_id

    def close_scope(self):
        self._open.pop()

    def lookup_current(self, name):
        """Symbol declared with `name` in the innermost scope, or None."""
        return self._open[-1][1].get(name)

    def lookup(self, name):
        """Visible symbol with `name`, innermost scope first, or None."""
        for _, symbols in reversed(self._open):
            if name in symbols:
                return symbols[name]
        return None

    def declare(self, name, data_type, line, column):
        symbol = Symbol(name, data_type, self.current_scope, line, column)
        self._open[-1][1][name] = symbol
        self.records.append(symbol)
        return symbol


# ---------------------------------------------------------------------------
# Results and errors
# ---------------------------------------------------------------------------

class SemanticError(Exception):
    """
    First semantic error found. `line`, `column` and `lexeme` come from the
    token responsible for it. str() gives "SDT error in line n".
    """

    def __init__(self, code, description, terminal):
        self.code = code
        self.description = description
        self.terminal = terminal
        self.line = terminal.line
        self.column = terminal.column
        self.lexeme = terminal.lexeme
        self.symbols = None          # symbol table up to the error
        super().__init__(f"SDT error in line {self.line}")

    def details(self):
        return (
            f"{self} (column {self.column}, {self.lexeme!r}): "
            f"{self.code} {self.description}"
        )


class SDTResult:
    """Outcome of a successful analysis."""

    message = "SDT Verified!"

    def __init__(self, symbols):
        self.symbols = symbols     # SymbolTable with every record


class _Expr:
    """Synthesized attributes of an expression node."""

    __slots__ = ("data_type", "literal_lexeme", "terminal")

    def __init__(self, data_type, terminal, literal_lexeme=None):
        self.data_type = data_type
        self.terminal = terminal            # first token, for error positions
        self.literal_lexeme = literal_lexeme


# ---------------------------------------------------------------------------
# Analyzer
# ---------------------------------------------------------------------------

# Production ids (team grammar, productions 0-50).
_P_PROGRAM = 1
_P_BLOCK = 2
_P_ITEMS_MORE, _P_ITEMS_EMPTY = 3, 4
_P_ITEM_DECL, _P_ITEM_STMT = 5, 6
_P_DECL = 7
_P_TYPES = {8: INT, 9: FLOAT, 10: CHAR}
_P_INIT, _P_INIT_EMPTY = 11, 12
_P_IF_ELSE = (17, 20)
_P_WHILE = (18, 21)
_P_IF = 19
_P_ASSIGN, _P_RETURN, _P_EMPTY = 22, 23, 24
_P_COMPARISON = (26, 27, 29, 30, 31, 32)
_P_ARITHMETIC = (34, 35, 37, 38)
_P_MODULO = 39
_P_SIGN = (41, 42)
_P_NOT = 43
_P_PRIMARY_ID = 45
_P_LITERALS = (46, 47, 48, 49)
_P_PARENS = 50
# Single-child productions that only pass through (statements or
# expressions): 13-16, 25, 28, 33, 36, 40, 44.
_P_PASS_STMT = (13, 14, 15, 16)
_P_PASS_EXPR = (25, 28, 33, 36, 40, 44)


class SemanticAnalyzer:
    """
    Usage:
        result = SemanticAnalyzer().analyze(parse_result.tree)
        print(result.message)          # SDT Verified!
    Raises SemanticError on the first semantic error.
    """

    def analyze(self, tree):
        self.symbols = SymbolTable()
        try:
            self._program(tree)
        except SemanticError as error:
            error.symbols = self.symbols
            raise
        return SDTResult(self.symbols)

    # -- structure ---------------------------------------------------------

    def _program(self, node):
        # 1  Program -> int main ( ) Block      (return type of main: int)
        self._expect(node, _P_PROGRAM)
        self._block(node.children[4])

    def _block(self, node):
        # 2  Block -> { Items }   new scope, closed when the block ends
        self.symbols.open_scope()
        self._items(node.children[1])
        self.symbols.close_scope()

    def _items(self, node):
        # 3  Items -> Items Item     4  Items -> epsilon
        # The list is left-recursive; walk it without recursion so long
        # programs do not hit Python's recursion limit, then visit the
        # items left to right (source order).
        items = []
        while node.production.id == _P_ITEMS_MORE:
            items.append(node.children[1])
            node = node.children[0]
        for item in reversed(items):
            self._item(item)

    def _item(self, node):
        # 5  Item -> Decl     6  Item -> Stmt
        child = node.children[0]
        if node.production.id == _P_ITEM_DECL:
            self._decl(child)
        else:
            self._stmt(child)

    def _decl(self, node):
        # 7  Decl -> Type ID Init ;
        type_node, id_node, init_node, _ = node.children
        data_type = _P_TYPES[type_node.production.id]       # 8, 9, 10
        name = id_node.lexeme
        if self.symbols.lookup_current(name) is not None:
            previous = self.symbols.lookup_current(name)
            self._fail("SEM001", f"'{name}' is already declared in this scope "
                       f"(line {previous.line})", id_node.terminal)
        # Insert before checking the initializer: int x = x; is accepted.
        symbol = self.symbols.declare(
            name, data_type, id_node.terminal.line, id_node.terminal.column
        )
        if init_node.production.id == _P_INIT:               # 11  Init -> = Expr
            value = self._expr(init_node.children[1])
            symbol.has_initializer = True
            symbol.initializer_type = value.data_type
            symbol.initializer_lexeme = value.literal_lexeme
            if not assignable(data_type, value.data_type):
                self._fail("SEM004", f"cannot initialize {data_type} "
                           f"'{name}' with {value.data_type}", id_node.terminal)
        # 12  Init -> epsilon: no initializer, nothing to check

    def _stmt(self, node):
        # Iterative over pass-through chains (Stmt -> Matched -> Simple ...)
        while node.production.id in _P_PASS_STMT:            # 13-16
            child = node.children[0]
            if child.symbol == "Block":
                self._block(child)
                return
            node = child
        pid = node.production.id
        if pid in _P_IF_ELSE:
            # 17/20  if ( Expr ) Matched else Matched|Unmatched
            self._condition(node.children[0], node.children[2])
            self._stmt(node.children[4])
            self._stmt(node.children[6])
        elif pid in _P_WHILE or pid == _P_IF:
            # 18/21  while ( Expr ) body     19  if ( Expr ) Stmt
            self._condition(node.children[0], node.children[2])
            self._stmt(node.children[4])
        elif pid == _P_ASSIGN:
            self._assign(node)
        elif pid == _P_RETURN:
            # 23  Simple -> return Expr ;
            value = self._expr(node.children[1])
            if not assignable(MAIN_RETURN_TYPE, value.data_type):
                self._fail("SEM007", f"main returns int, not {value.data_type}",
                           node.children[0].terminal)
        elif pid == _P_EMPTY:
            pass                                             # 24  Simple -> ;
        else:
            raise ValueError(f"Unexpected statement production {pid}")

    def _assign(self, node):
        # 22  Simple -> ID = Expr ;
        id_node, _, expr_node, _ = node.children
        symbol = self._lookup(id_node)
        value = self._expr(expr_node)
        if not assignable(symbol.data_type, value.data_type):
            self._fail("SEM003", f"cannot assign {value.data_type} to "
                       f"{symbol.data_type} '{symbol.name}'", id_node.terminal)

    def _condition(self, keyword_node, expr_node):
        value = self._expr(expr_node)
        if value.data_type not in NUMERIC_TYPES:
            self._fail("SEM006", f"condition of '{keyword_node.lexeme}' must be "
                       f"numeric, not {value.data_type}", keyword_node.terminal)

    # -- expressions -------------------------------------------------------

    def _expr(self, node):
        # Pass-through chains (Expr -> Equality -> ... -> Primary) are walked
        # without recursion; they propagate data_type and literal_lexeme.
        while node.production is not None and node.production.id in _P_PASS_EXPR:
            node = node.children[0]
        pid = node.production.id

        if pid in _P_LITERALS:
            # 46-49  Primary -> INT | FLOAT | CHAR | STRING
            leaf = node.children[0]
            return _Expr(_LITERAL_TYPES[leaf.symbol], leaf.terminal, leaf.lexeme)

        if pid == _P_PRIMARY_ID:
            # 45  Primary -> ID
            leaf = node.children[0]
            symbol = self._lookup(leaf)
            return _Expr(symbol.data_type, leaf.terminal)

        if pid == _P_PARENS:
            # 50  Primary -> ( Expr )   no new scope
            inner = self._expr(node.children[1])
            return _Expr(inner.data_type, node.children[0].terminal,
                         inner.literal_lexeme)

        if pid in _P_SIGN or pid == _P_NOT:
            # 41/42  Unary -> + Unary | - Unary     43  Unary -> ! Unary
            operator = node.children[0]
            operand = self._expr(node.children[1])
            self._require(operand, NUMERIC_TYPES, operator, "a number")
            result = INT if pid == _P_NOT else promote(operand.data_type)
            return _Expr(result, operator.terminal)

        # Binary operators: left op right
        left_node, operator, right_node = node.children
        left = self._expr(left_node)
        right = self._expr(right_node)

        if pid == _P_MODULO:
            # 39  Mul -> Mul % Unary     char/int only, result int
            self._require(left, INTEGRAL_TYPES, operator, "char or int")
            self._require(right, INTEGRAL_TYPES, operator, "char or int")
            return _Expr(INT, left.terminal)

        self._require(left, NUMERIC_TYPES, operator, "a number")
        self._require(right, NUMERIC_TYPES, operator, "a number")

        if pid in _P_COMPARISON:
            # 26, 27, 29-32  equality and relations: result int
            return _Expr(INT, left.terminal)
        if pid in _P_ARITHMETIC:
            # 34, 35, 37, 38  + - * /
            result = FLOAT if FLOAT in (left.data_type, right.data_type) else INT
            return _Expr(result, left.terminal)
        raise ValueError(f"Unexpected expression production {pid}")

    # -- helpers -----------------------------------------------------------

    def _lookup(self, id_node):
        symbol = self.symbols.lookup(id_node.lexeme)
        if symbol is None:
            self._fail("SEM002", f"'{id_node.lexeme}' is not declared",
                       id_node.terminal)
        return symbol

    def _require(self, value, allowed, operator_node, wanted):
        if value.data_type not in allowed:
            self._fail("SEM005", f"operator '{operator_node.lexeme}' needs "
                       f"{wanted}, not {value.data_type}", operator_node.terminal)

    @staticmethod
    def _expect(node, production_id):
        if node.production is None or node.production.id != production_id:
            raise ValueError(f"Expected production {production_id} at {node!r}")

    @staticmethod
    def _fail(code, description, terminal):
        raise SemanticError(code, description, terminal)

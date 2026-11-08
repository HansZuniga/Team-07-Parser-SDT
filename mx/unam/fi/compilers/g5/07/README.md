# unam.fi.compilers.g5.07 — Parser & SDT

## Estructura

```
07/
├── resources/
│   ├── keywords.txt          # print, int, float, char, return, if, else, while
│   └── parser/               # gramatica.json + action_goto.json (Model Designer, #2-#4)
├── src/main/
│   ├── lexer.py              # Lexer del proyecto anterior (+ float/char/while y 'c')
│   ├── token_stream.py       # Puente lexer -> parser: tokens a terminales + $
│   ├── clr1_parser.py        # Motor CLR(1): shift/reduce/goto/accept, árbol y traza
│   ├── sdt.py                # SDT: tabla de símbolos, ámbitos y tipos
│   └── main.py               # CLI
├── examples/
│   └── example_profesor.c
└── tests/                    # pytest
    └── cases/                # programas de prueba + salida esperada (#10)
```

## Lexer → parser (issue #7)

El parser no vuelve a hacer análisis léxico: `token_stream.py` ejecuta el
lexer, se detiene si hubo errores léxicos (`Lexical error in line n`) y
traduce cada token al terminal de la gramática:

| Token del lexer          | Terminal     |
|--------------------------|--------------|
| `KEYWORD 'int'`          | `int`        |
| `IDENTIFIER 'main'`      | `main`       |
| `IDENTIFIER 'x'`         | `ID`         |
| `CONSTANT '10'`          | `INT`        |
| `CONSTANT '3.5'`         | `FLOAT`      |
| `LITERAL 'a'`            | `CHAR`       |
| `LITERAL "hola"`         | `STRING`     |
| `OPERATOR '='`           | `=`          |
| `PUNCTUATION ';'`        | `;`          |
| fin de la entrada        | `$`          |

Cada `Terminal` conserva el token original (lexema, línea, columna) para los
mensajes de error del parser y para el SDT.

> Los nombres de los terminales son los de la gramática CLR(1) del equipo
> (producciones 0-50, issue #2). `main` sigue siendo `IDENTIFIER` en el
> lexer (en C no es palabra reservada); solo su terminal es `main`, porque
> la gramática lo espera en `int main ( ) Block`. El lexer reconoce además
> los operadores `%` y `!` que usa la gramática.

```python
from token_stream import tokenize_source, LexicalError

terminals = tokenize_source("int x = 10;")
[t.symbol for t in terminals]   # ['int', 'ID', '=', 'INT', ';', '$']
```

## Motor CLR(1) (issue #5)

`clr1_parser.py` no calcula la colección LR(1): lee la gramática y la tabla
ACTION/GOTO del Model Designer desde `resources/parser/`:

- `gramatica.json`: producciones `{id, lhs, rhs}` (rhs vacío = epsilon).
- `action_goto.json`: `action` con `["s", n]`, `["r", p]` o `["acc", 0]` y
  `goto` con `{state, nonterminal, target}`. Si una celda trae más de una
  acción (conflicto), la tabla se rechaza.

En cada paso consulta `ACTION[estado, terminal]`: *shift* apila el estado y
avanza; *reduce* saca `|rhs|` estados y apila `GOTO[estado, lhs]`; *accept*
termina con `Parsing Success!`; una celda vacía da `Parsing error in line n`.

Cada reducción crea un nodo del árbol (`ParseNode`: símbolo, producción,
hijos y, en las hojas, el `Terminal` con lexema y línea). La raíz es
`Program` y queda lista para el SDT (#8).

**Línea del error.** Un `;` faltante se detecta hasta leer el siguiente
token, que suele estar en la línea de abajo. El parser prueba insertar un
`;`: si con él el token siguiente sí puede continuar, reporta la línea del
token anterior (donde faltó el `;`). Si no, reporta la línea del token
inesperado.

```python
from token_stream import tokenize_source
from clr1_parser import Parser, ParseError

parser = Parser()
try:
    result = parser.parse(tokenize_source(codigo), trace=True)
    print(result.message)        # Parsing Success!
    result.tree                  # raíz del árbol
    result.steps                 # traza paso a paso
except ParseError as error:
    print(error)                 # Parsing error in line n
```

## SDT / análisis semántico (issue #8)

`sdt.py` recorre el árbol que entrega el parser y aplica en cada nodo la
acción semántica de su producción, según el documento del equipo
"4. Reglas SDT y tabla de símbolos". Solo revisa nombres y tipos; no
ejecuta el programa.

- **Ámbitos:** cada `Block` abre uno (el de `main` es el 0). Se busca del
  más interno al más externo; se permite sombrear en un bloque interior,
  pero no declarar dos veces en el mismo. La tabla conserva todos los
  registros aunque el bloque ya se haya cerrado.
- **Tipos:** inicializar, asignar y `return` admiten la misma clase o una
  más amplia (`char -> int -> float`). Las cadenas no se asignan a nada.

| Destino \ origen | char | int | float |
|------------------|------|-----|-------|
| char             | sí   | no  | no    |
| int              | sí   | sí  | no    |
| float            | sí   | sí  | sí    |

- `+ - * /` piden números (char sube a int; float si hay algún float);
  `%` solo char/int; comparaciones y `!` dan int; las condiciones de
  `if`/`while` deben ser numéricas; `return` debe ser compatible con int.

Se reporta el primer error, con la línea del token responsable:

| Código | Error | Ejemplo |
|--------|-------|---------|
| SEM001 | declaración duplicada en el mismo ámbito | `int x; int x;` |
| SEM002 | identificador no declarado | `y = 1;` |
| SEM003 | asignación incompatible | `char c; c = c + 1;` |
| SEM004 | inicialización incompatible | `int x = "hello";` |
| SEM005 | tipo inválido para un operador | `float f; int m = f % 2;` |
| SEM006 | condición no numérica | `if ("a") ;` |
| SEM007 | `return` no compatible con int | `return 2.5;` |

SEM001-SEM004 vienen del documento del equipo; SEM005-SEM007 nombran las
demás revisiones que pide ese documento.

```
Parsing Success!
SDT Verified!            # o: SDT error in line n
```

## Uso

Desde `src/main/`:

```bash
python main.py                                  # ejemplo del profesor
python main.py --file programa.c                # tabla de tokens
python main.py --text "int x = 10;" --terminals # lo que recibe el parser
python main.py --file programa.c --parse        # Parsing Success! / error
python main.py --file programa.c --trace        # pasos shift/reduce
python main.py --file programa.c --tree         # árbol de parseo
python main.py --file programa.c --sdt          # parser + SDT
python main.py --file programa.c --symbols      # parser + SDT + tabla de símbolos
```

## Pruebas

Desde `07/`:

```bash
python -m pytest tests
```

Las pruebas con la gramática completa se saltan (`skipped`) si
`resources/parser/` todavía no tiene los archivos del Model Designer.

### Casos de prueba (issue #10)

`tests/cases/` tiene 42 programas en las cuatro categorías del proyecto.
Cada caso es un `.c` y un `.expected` con la salida exacta que debe dar
`main.py --file <caso> --sdt`; `descriptions.json` describe cada uno.

| Carpeta | Categoría | Salida |
|---------|-----------|--------|
| `valid/` (10) | sintaxis y semántica válidas | `Parsing Success!` + `SDT Verified!` |
| `syntax/` (12) | sintaxis inválida | `Parsing error in line n` |
| `semantic/` (13) | sintaxis válida, semántica inválida | `Parsing Success!` + `SDT error in line n` |
| `lexical/` (7) | errores léxicos | `Lexical error in line n` |

```bash
python tests/cases/run_cases.py              # esperado vs. obtenido
python tests/cases/run_cases.py --markdown   # regenera tests/cases/RESULTS.md
```

`tests/test_cases.py` corre los mismos casos dentro de pytest.
`RESULTS.md` documenta la salida esperada y la obtenida de cada caso.

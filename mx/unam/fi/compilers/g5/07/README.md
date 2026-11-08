# unam.fi.compilers.g5.07 — Parser & SDT

## Estructura

```
07/
├── resources/
│   └── keywords.txt          # print, int, float, char, return, if, else, while
├── src/main/
│   ├── lexer.py              # Lexer del proyecto anterior (+ float/char/while y 'c')
│   ├── token_stream.py       # Puente lexer -> parser: tokens a terminales + $
│   └── main.py               # CLI
├── examples/
│   └── example_profesor.c
└── tests/                    # pytest
```

## Lexer → parser (issue #7)

El parser no vuelve a hacer análisis léxico: `token_stream.py` ejecuta el
lexer, se detiene si hubo errores léxicos (`Lexical error in line n`) y
traduce cada token al terminal de la gramática:

| Token del lexer          | Terminal     |
|--------------------------|--------------|
| `KEYWORD 'int'`          | `int`        |
| `IDENTIFIER 'x'`         | `id`         |
| `CONSTANT '10'`/`'3.5'`  | `num`        |
| `LITERAL 'a'`            | `char_lit`   |
| `LITERAL "hola"`         | `string_lit` |
| `OPERATOR '='`           | `=`          |
| `PUNCTUATION ';'`        | `;`          |
| fin de la entrada        | `$`          |

Cada `Terminal` conserva el token original (lexema, línea, columna) para los
mensajes de error del parser y para el SDT.

> Los nombres `id`, `num`, `char_lit` y `string_lit` son provisionales hasta
> que quede la gramática final (issue #2). Se cambian en las constantes al
> inicio de `token_stream.py`.

```python
from token_stream import tokenize_source, LexicalError

terminals = tokenize_source("int x = 10;")
[t.symbol for t in terminals]   # ['int', 'id', '=', 'num', ';', '$']
```

## Uso

Desde `src/main/`:

```bash
python main.py                                  # ejemplo del profesor
python main.py --file programa.c                # tabla de tokens
python main.py --text "int x = 10;" --terminals # lo que recibe el parser
```

## Pruebas

Desde `07/`:

```bash
python -m pytest tests
```

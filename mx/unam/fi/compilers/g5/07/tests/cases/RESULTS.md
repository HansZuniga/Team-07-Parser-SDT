# Resultados de los casos de prueba (issue #10)

Generado con `python tests/cases/run_cases.py --markdown`. Cada caso
se ejecuta con el programa real (`main.py --file <caso> --sdt`) y su
salida se compara con el archivo `.expected`.

**42 de 42 casos correctos.**

## 1. Sintaxis y semántica válidas

| Caso | Descripción | Salida esperada | Salida obtenida | OK |
|------|-------------|-----------------|-----------------|----|
| `01_minimal` | Programa mínimo: main con bloque vacío. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `02_declarations` | Declaraciones int/float/char con y sin inicializador. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `03_expressions` | Precedencia, paréntesis, unarios, % y comparaciones. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `04_if_else` | if, if/else e if anidado sin llaves (dangling else). | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `05_while` | while con y sin llaves, y anidado. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `06_scopes` | Bloques anidados, sombreado y variables externas visibles. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `07_widening` | Ampliación permitida: char -> int -> float. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `08_document_example` | Ejemplo del documento de reglas SDT del equipo. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `09_empty_statements` | Sentencias vacías y bloques vacíos. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |
| `10_full_program` | Programa completo con todo el subconjunto. | Parsing Success!<br>SDT Verified! | Parsing Success!<br>SDT Verified! | ✅ |

## 2. Sintaxis inválida

| Caso | Descripción | Salida esperada | Salida obtenida | OK |
|------|-------------|-----------------|-----------------|----|
| `01_missing_semicolon_declaration` | Falta ';' al final de una declaración (línea 2). | Parsing error in line 2 | Parsing error in line 2 | ✅ |
| `02_missing_semicolon_before_brace` | Falta ';' en el return antes de '}' (línea 3). | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `03_missing_parenthesis` | Falta ')' en la condición del if. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `04_missing_closing_brace` | Falta la '}' final del programa. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `05_code_after_main` | Código después de que termina main. | Parsing error in line 4 | Parsing error in line 4 | ✅ |
| `06_missing_expression` | Asignación sin valor. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `07_compound_assignment` | '+=' no está en el subconjunto. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `08_function_call` | Llamadas a funciones no están en el subconjunto. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `09_missing_return_type` | main sin 'int' al inicio. | Parsing error in line 1 | Parsing error in line 1 | ✅ |
| `10_else_without_if` | else sin if. | Parsing error in line 3 | Parsing error in line 3 | ✅ |
| `11_declaration_without_name` | Declaración sin identificador. | Parsing error in line 2 | Parsing error in line 2 | ✅ |
| `12_unbalanced_parentheses` | Paréntesis de más en una expresión. | Parsing error in line 3 | Parsing error in line 3 | ✅ |

## 3. Sintaxis válida, semántica inválida

| Caso | Descripción | Salida esperada | Salida obtenida | OK |
|------|-------------|-----------------|-----------------|----|
| `01_duplicate_declaration` | SEM001: x declarada dos veces en el mismo bloque. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `02_undeclared_variable` | SEM002: y nunca se declaró. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `03_out_of_scope` | SEM002: z solo existe dentro de su bloque. | Parsing Success!<br>SDT error in line 5 | Parsing Success!<br>SDT error in line 5 | ✅ |
| `04_undeclared_in_expression` | SEM002: variable no declarada dentro de una expresión. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `05_assignment_type_mismatch` | SEM003: float no cabe en int (estrechamiento). | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `06_char_plus_one` | SEM003: char + 1 da int y no cabe en char. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `07_string_initialization` | SEM004: una cadena no se asigna a int. | Parsing Success!<br>SDT error in line 2 | Parsing Success!<br>SDT error in line 2 | ✅ |
| `08_narrowing_initialization` | SEM004: valor int inválido para char. | Parsing Success!<br>SDT error in line 2 | Parsing Success!<br>SDT error in line 2 | ✅ |
| `09_modulo_with_float` | SEM005: % no acepta float. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `10_string_in_arithmetic` | SEM005: una cadena en una suma. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `11_string_condition` | SEM006: la condición del while no es numérica. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `12_return_float` | SEM007: main regresa int, no float. | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |
| `13_first_error_only` | Hay dos errores; solo se reporta el primero (línea 3). | Parsing Success!<br>SDT error in line 3 | Parsing Success!<br>SDT error in line 3 | ✅ |

## 4. Errores léxicos

| Caso | Descripción | Salida esperada | Salida obtenida | OK |
|------|-------------|-----------------|-----------------|----|
| `01_invalid_character` | '@' no pertenece al lenguaje. | Lexical error in line 3 | Lexical error in line 3 | ✅ |
| `02_malformed_number` | Número mal formado: 12abc. | Lexical error in line 2 | Lexical error in line 2 | ✅ |
| `03_unterminated_string` | Cadena sin comilla de cierre. | Lexical error in line 3 | Lexical error in line 3 | ✅ |
| `04_malformed_char` | Literal de carácter con dos caracteres. | Lexical error in line 2 | Lexical error in line 2 | ✅ |
| `05_logical_and` | '&&' no está en el subconjunto: '&' es error léxico. | Lexical error in line 3 | Lexical error in line 3 | ✅ |
| `06_before_syntax_error` | Hay error de sintaxis (línea 2) y léxico (línea 4): el léxico detiene todo antes del parser. | Lexical error in line 4 | Lexical error in line 4 | ✅ |
| `07_before_semantic_error` | Hay error semántico (línea 2) y léxico (línea 3): el parser y el SDT nunca corren. | Lexical error in line 3 | Lexical error in line 3 | ✅ |

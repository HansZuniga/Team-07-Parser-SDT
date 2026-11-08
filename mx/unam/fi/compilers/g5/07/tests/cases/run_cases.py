"""
Runs every test case of tests/cases/ through the real program
(src/main/main.py --file <case> --sdt) and compares its output with the
case's .expected file (issue #10).

    python tests/cases/run_cases.py              # summary in the terminal
    python tests/cases/run_cases.py --markdown   # also writes RESULTS.md

Each case is a pair:
    <category>/<name>.c         C-subset source
    <category>/<name>.expected  exact expected output
and descriptions.json holds a one-line description of every case.
"""

import json
import subprocess
import sys
from pathlib import Path

CASES_DIR = Path(__file__).resolve().parent
MAIN = CASES_DIR.parents[1] / "src" / "main" / "main.py"
RESULTS = CASES_DIR / "RESULTS.md"

CATEGORIES = [
    ("valid", "1. Sintaxis y semántica válidas"),
    ("syntax", "2. Sintaxis inválida"),
    ("semantic", "3. Sintaxis válida, semántica inválida"),
    ("lexical", "4. Errores léxicos"),
]


def case_files():
    """Every .c case, in category order and then by name."""
    return [
        path
        for category, _ in CATEGORIES
        for path in sorted((CASES_DIR / category).glob("*.c"))
    ]


def descriptions():
    with open(CASES_DIR / "descriptions.json", encoding="utf-8") as file:
        return {entry["file"]: entry["description"] for entry in json.load(file)}


def expected_output(case):
    return case.with_suffix(".expected").read_text(encoding="utf-8").splitlines()


def actual_output(case):
    """Run the real program on `case` and return its output lines."""
    completed = subprocess.run(
        [sys.executable, str(MAIN), "--file", str(case), "--sdt"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=MAIN.parent,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{case.name} crashed:\n{completed.stderr}")
    return completed.stdout.splitlines()


def relative(case):
    return case.relative_to(CASES_DIR).as_posix()


def run():
    rows = []
    for case in case_files():
        expected = expected_output(case)
        actual = actual_output(case)
        rows.append((case, expected, actual, expected == actual))
    return rows


def markdown(rows):
    info = descriptions()
    passed = sum(ok for *_, ok in rows)
    lines = [
        "# Resultados de los casos de prueba (issue #10)",
        "",
        "Generado con `python tests/cases/run_cases.py --markdown`. Cada caso",
        "se ejecuta con el programa real (`main.py --file <caso> --sdt`) y su",
        "salida se compara con el archivo `.expected`.",
        "",
        f"**{passed} de {len(rows)} casos correctos.**",
    ]
    for category, title in CATEGORIES:
        lines += [
            "",
            f"## {title}",
            "",
            "| Caso | Descripción | Salida esperada | Salida obtenida | OK |",
            "|------|-------------|-----------------|-----------------|----|",
        ]
        for case, expected, actual, ok in rows:
            if case.parent.name != category:
                continue
            lines.append(
                f"| `{case.stem}` | {info.get(relative(case), '')} | "
                f"{'<br>'.join(expected)} | {'<br>'.join(actual)} | "
                f"{'✅' if ok else '❌'} |"
            )
    return "\n".join(lines) + "\n"


def main():
    rows = run()
    for case, expected, actual, ok in rows:
        status = "OK  " if ok else "FAIL"
        print(f"{status} {relative(case):<45} {' / '.join(actual)}")
        if not ok:
            print(f"     expected: {' / '.join(expected)}")
    passed = sum(ok for *_, ok in rows)
    print(f"\n{passed}/{len(rows)} cases passed")
    if "--markdown" in sys.argv:
        RESULTS.write_text(markdown(rows), encoding="utf-8", newline="\n")
        print(f"Written {RESULTS}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())

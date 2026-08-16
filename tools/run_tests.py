#!/usr/bin/env python3
"""
Regression runner for the whole project.

    python3 tools/run_tests.py            # everything
    python3 tools/run_tests.py phase2     # parser only
    python3 tools/run_tests.py phase3     # code generator only

Phase 2 is checked against golden files: every case under
`phase2-parser/tests/` carries the parse tree and the syntax-error list the
parser is expected to produce, and the runner diffs the real output against
them.

Phase 3 is checked end to end: each example is compiled and the resulting
three-address code is executed by `tools/tester.py`, then the printed values
are compared with what the example is documented to produce.

Each compiler reads `input.txt` from its working directory, so every case is
run inside a scratch directory that holds a copy of the compiler.
"""

import os
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSER = os.path.join(ROOT, 'phase2-parser', 'compiler.py')
CODEGEN = os.path.join(ROOT, 'phase3-codegen', 'compiler.py')
TESTER = os.path.join(ROOT, 'tools', 'tester.py')

GREEN, RED, DIM, RESET = '\033[32m', '\033[31m', '\033[2m', '\033[0m'
if not sys.stdout.isatty():
    GREEN = RED = DIM = RESET = ''

# Expected stdout of each phase 3 example once its generated code is executed.
# `None` means the program is expected to be rejected before code generation.
PHASE3_EXPECTED = {
    'factorial': ['120'],
    'switch-goto': ['20'],
    'bubble-sort': ['1', '2', '5', '8', '9'],
    'semantic-errors': None,
}


def compile_in(workdir, compiler, source):
    """Copy the compiler next to `source` and run it. Returns the workdir."""
    shutil.copy(compiler, os.path.join(workdir, 'compiler.py'))
    shutil.copy(source, os.path.join(workdir, 'input.txt'))
    result = subprocess.run(
        [sys.executable, 'compiler.py'],
        cwd=workdir, capture_output=True, text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or 'compiler exited non-zero')
    return workdir


def normalise(text):
    """Compare ignoring trailing whitespace and a trailing newline."""
    return [line.rstrip() for line in text.rstrip().splitlines()]


def read(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def run_phase2():
    """Diff parser output against the golden files for every case."""
    root = os.path.join(ROOT, 'phase2-parser', 'tests')
    cases = []
    for suite in sorted(os.listdir(root)):
        suite_dir = os.path.join(root, suite)
        if not os.path.isdir(suite_dir):
            continue
        for case in sorted(os.listdir(suite_dir)):
            case_dir = os.path.join(suite_dir, case)
            if os.path.isdir(case_dir):
                cases.append((f'{suite}/{case}', case_dir))

    failures = []
    for name, case_dir in cases:
        with tempfile.TemporaryDirectory() as workdir:
            try:
                compile_in(workdir, PARSER, os.path.join(case_dir, 'input.txt'))
            except RuntimeError as exc:
                failures.append((name, str(exc)))
                print(f'{RED}FAIL{RESET} phase2 {name}  ({exc})')
                continue

            bad = []
            for artefact in ('parse_tree.txt', 'syntax_errors.txt'):
                actual = normalise(read(os.path.join(workdir, artefact)))
                expected = normalise(read(os.path.join(case_dir, artefact)))
                if actual != expected:
                    bad.append(artefact)

        if bad:
            failures.append((name, 'mismatch in ' + ', '.join(bad)))
            print(f'{RED}FAIL{RESET} phase2 {name}  ({", ".join(bad)})')
        else:
            print(f'{GREEN}ok{RESET}   phase2 {name}')

    return len(cases), failures


def run_phase3():
    """Compile each example, execute its code, compare the printed values."""
    root = os.path.join(ROOT, 'phase3-codegen', 'examples')
    failures = []
    names = sorted(PHASE3_EXPECTED)

    for name in names:
        expected = PHASE3_EXPECTED[name]
        with tempfile.TemporaryDirectory() as workdir:
            try:
                compile_in(workdir, CODEGEN, os.path.join(root, name, 'input.txt'))
            except RuntimeError as exc:
                failures.append((name, str(exc)))
                print(f'{RED}FAIL{RESET} phase3 {name}  ({exc})')
                continue

            errors = read(os.path.join(workdir, 'semantic_errors.txt')).strip()
            rejected = 'semantically correct' not in errors

            if expected is None:
                if rejected:
                    count = len(errors.splitlines())
                    print(f'{GREEN}ok{RESET}   phase3 {name} '
                          f'{DIM}(rejected, {count} semantic errors){RESET}')
                else:
                    failures.append((name, 'expected semantic errors, got none'))
                    print(f'{RED}FAIL{RESET} phase3 {name}  (expected semantic errors)')
                continue

            if rejected:
                failures.append((name, 'unexpected semantic errors'))
                print(f'{RED}FAIL{RESET} phase3 {name}  (unexpected semantic errors)')
                continue

            result = subprocess.run(
                [sys.executable, TESTER, os.path.join(workdir, 'output.txt')],
                capture_output=True, text=True,
            )
            actual = result.stdout.split()

        if actual == expected:
            print(f'{GREEN}ok{RESET}   phase3 {name} {DIM}-> {" ".join(actual)}{RESET}')
        else:
            failures.append((name, f'printed {actual}, expected {expected}'))
            print(f'{RED}FAIL{RESET} phase3 {name}  '
                  f'(printed {actual}, expected {expected})')

    return len(names), failures


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    total, failures = 0, []

    if which in ('all', 'phase2'):
        count, failed = run_phase2()
        total += count
        failures += failed
    if which in ('all', 'phase3'):
        count, failed = run_phase3()
        total += count
        failures += failed

    print()
    if failures:
        print(f'{RED}{len(failures)} of {total} cases failed{RESET}')
        sys.exit(1)
    print(f'{GREEN}all {total} cases passed{RESET}')


if __name__ == '__main__':
    main()

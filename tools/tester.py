#!/usr/bin/env python3
"""
A small interpreter for the three-address code emitted by phase 3.

The course supplies its own `Tester` binary for grading; this is a standalone
re-implementation of the same ten instructions so that anyone cloning this
repository can actually *run* a generated `output.txt` and see the result.

    python3 tools/tester.py output.txt

It is a development helper and plays no part in the compiler itself.

Memory model (matching the code generator): a flat word-addressed store,
four bytes per integer, everything allocated statically except the runtime
stack that phase 3 maintains for recursive calls.

Operand forms:
    100     direct    - the word stored at address 100
    @100    indirect  - the word at the address held in 100
    #100    immediate - the literal 100
"""

import re
import sys

OPS_BINARY = {
    'ADD':  lambda a, b: a + b,
    'SUB':  lambda a, b: a - b,
    'MULT': lambda a, b: a * b,
    'DIV':  lambda a, b: int(a / b) if b else 0,
    'EQ':   lambda a, b: 1 if a == b else 0,
    'LT':   lambda a, b: 1 if a < b else 0,
}

LINE_RE = re.compile(r'^(\d+)\s*\((.*)\)\s*$')


def load(path):
    """Parse output.txt into {line number: [op, arg1, arg2, arg3]}."""
    program = {}
    with open(path, encoding='utf-8') as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            if 'has not been generated' in line:
                return None
            match = LINE_RE.match(line)
            if not match:
                raise SystemExit(f'malformed line in {path}: {raw!r}')
            args = [part.strip() for part in match.group(2).split(',')]
            args += [''] * (4 - len(args))
            program[int(match.group(1))] = args[:4]
    return program


def run(program, step_limit=50_000_000):
    """Execute the program and return the list of values it printed."""
    memory = {}
    printed = []

    def value(operand):
        if operand.startswith('#'):
            return int(operand[1:])
        if operand.startswith('@'):
            return memory.get(memory.get(int(operand[1:]), 0), 0)
        return memory.get(int(operand), 0)

    def address(operand):
        if operand.startswith('@'):
            return memory.get(int(operand[1:]), 0)
        return int(operand)

    pc = 0
    steps = 0
    while pc in program:
        steps += 1
        if steps > step_limit:
            raise SystemExit('step limit exceeded - the program does not terminate')

        op, a1, a2, a3 = program[pc]

        if op in OPS_BINARY:
            memory[address(a3)] = OPS_BINARY[op](value(a1), value(a2))
        elif op == 'ASSIGN':
            memory[address(a2)] = value(a1)
        elif op == 'PRINT':
            printed.append(value(a1))
        elif op == 'JP':
            pc = address(a1)
            continue
        elif op == 'JPF':
            if value(a1) == 0:
                pc = address(a2)
                continue
        else:
            raise SystemExit(f'unknown instruction {op!r} at line {pc}')

        pc += 1

    return printed


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else 'output.txt'
    program = load(path)
    if program is None:
        print('the input program had semantic errors; no code was generated')
        return
    for value in run(program):
        print(value)


if __name__ == '__main__':
    main()

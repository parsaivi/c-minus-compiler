# Phase 3 — Semantic Analysis and Code Generation

The back end walks the parse tree, checks the program for six classes of
semantic error, and emits three-address code. Both optional parts of the
assignment are implemented: the semantic analyser, and code generation for
**recursive** functions.

Source: [`phase3-codegen/compiler.py`](../phase3-codegen/compiler.py)

## Target instruction set

Ten instructions, each a four-field tuple, numbered from zero:

| Instruction | Effect |
| --- | --- |
| `(ADD, a, b, r)` | `r ← a + b` |
| `(SUB, a, b, r)` | `r ← a - b` |
| `(MULT, a, b, r)` | `r ← a × b` |
| `(DIV, a, b, r)` | `r ← a ÷ b` |
| `(EQ, a, b, r)` | `r ← 1 if a = b else 0` |
| `(LT, a, b, r)` | `r ← 1 if a < b else 0` |
| `(ASSIGN, a, r, )` | `r ← a` |
| `(JP, L, , )` | jump to line `L` |
| `(JPF, a, L, )` | jump to `L` if `a` is zero |
| `(PRINT, a, , )` | print `a` |

Three addressing modes: `100` is direct, `@100` is indirect (the address held
in 100), `#100` is an immediate literal. Memory is a flat word-addressed store,
four bytes per integer.

## Memory layout

```
      4   stack pointer  (SP)
      8   frame pointer  (FP)
     12   return-address scratch
  16– 96  scratch cells for address arithmetic
    100+  global variables and arrays
  20000+  runtime stack — one activation record per active call
```

The scratch region exists because the instruction set has no register-plus-
offset addressing. Reaching a local variable means computing `FP + offset` into
a scratch cell first, then dereferencing it with `@`. That is why the generated
code contains so many `ADD` instructions: each one is an address computation,
not arithmetic from the source program. Scratch cells are handed out
round-robin and are dead the moment the instruction that consumes them
executes.

## Recursion

The straightforward way to compile this language is to give every variable a
fixed absolute address. That works right up until a function calls itself: the
second invocation overwrites the first one's locals, and the recursion returns
garbage.

So locals, parameters and temporaries are addressed **relative to the frame
pointer** instead, and each call gets a fresh activation record on a runtime
stack:

```
FP +  0   return address
FP +  4   return value
FP +  8   caller's saved FP
FP + 12   parameters
   …      locals
   …      temporaries
```

`new_temp()` allocates an FP-relative slot whenever the generator is inside a
function, and an absolute address only at global scope — so even intermediate
expression results are per-invocation.

**Call sequence** (in the caller): evaluate the arguments and write them into
the callee's parameter slots; save the current FP; leave a placeholder for the
return address; set `FP ← SP` and bump `SP` past the new frame; `JP` to the
function. The return address is backpatched with the line after the jump, which
is only known once the jump has been emitted.

**Return sequence** (in the callee): write the return value to `FP + 4`; copy
FP into a scratch cell (it is about to be overwritten); load the saved return
address; restore `SP ← FP` and `FP ← saved FP`; then `JP @` through the return
address. The caller picks the return value out of `SP + 4`, which still points
at the frame that just went away.

This is a genuine calling convention rather than inlining, so mutual recursion
and arbitrary call depth both work.

`phase3-codegen/examples/factorial/` computes `fact(5)` and prints `120`.

## Control flow

Everything is compiled with backpatching: emit the jump with a placeholder
target, remember its line number, and fill in the address once the destination
is known.

- **`if` / `else`** — `JPF` over the then-branch; when an `else` exists, a `JP`
  at the end of the then-branch skips it.
- **`while`** — condition, `JPF` to the exit, body, `JP` back to the condition.
- **`break`** — pushed onto a stack of pending jumps, all patched to the loop
  exit when the enclosing loop closes.
- **`switch`** — each `case` compiles to an `EQ` against the switch expression
  and a `JPF` to the next case's test. C's fallthrough semantics are preserved:
  the jump at the end of a case body targets the *next case's body*, not the end
  of the switch, so control falls through unless a `break` cuts it short.
  `default` runs when no case matched, and the last body falls through into it.
- **`goto` / labels** — a label may be referenced before it is defined, so
  forward `goto`s are collected in a fixup list and patched at the end of the
  enclosing function, once every label position is known.

`phase3-codegen/examples/switch-goto/` exercises `switch`, `case`, `default`,
`break` and a forward `goto` in one program.

## Semantic checks

All six checks run in the same pass as code generation. Errors are written to
`semantic_errors.txt`; if any occur, `output.txt` is emptied and contains only
`The output code has not been generated.` — a program that does not type-check
produces no code.

| Check | Message |
| --- | --- |
| Undeclared identifier | `#N : Semantic Error! 'x' is not defined.` |
| `void` variable | `#N : Semantic Error! Illegal type of void for 'x'.` |
| Argument count | `#N : Semantic Error! Mismatch in numbers of arguments of 'f'.` |
| `break` outside a loop | `#N : Semantic Error! No 'while' found for 'break'.` |
| Operand type mismatch | `#N : Semantic Error! Type mismatch in operands, Got array instead of int.` |
| Argument type mismatch | `#N : Semantic Error! Mismatch in type of argument 2 of 'f'. Expected 'int' but got 'array' instead.` |

Scope handling is two-level, matching the language: a global table plus the
current function's local table, with locals shadowing globals. Arrays passed as
parameters decay to a base address, so an array argument has type `array` and
an `int` argument does not — which is what the argument-type check compares.

`phase3-codegen/examples/semantic-errors/` triggers all six in one file.

## Output files

| File | Content |
| --- | --- |
| `output.txt` | numbered three-address code, or the "not generated" line |
| `semantic_errors.txt` | one error per line, or `The input program is semantically correct.` |

Phase 3 also still writes `parse_tree.txt` and `syntax_errors.txt` — it
contains the full pipeline, scanner and parser included.

## Running the generated code

The course grades phase 3 with its own `Tester` interpreter. This repository
ships an equivalent one so results are reproducible without it:

```bash
cd phase3-codegen
cp examples/factorial/input.txt .
python3 compiler.py
python3 ../tools/tester.py output.txt      # 120
```

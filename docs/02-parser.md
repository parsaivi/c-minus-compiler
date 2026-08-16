# Phase 2 — LL(1) Parser

A table-driven predictive parser. It pulls tokens from the phase 1 scanner,
builds a parse tree, and recovers from syntax errors in panic mode.

Source: [`phase2-parser/compiler.py`](../phase2-parser/compiler.py)

## Why LL(1)

The grammar is fixed by the assignment — 57 productions, already
left-factored and free of left recursion. That is what makes a single token of
lookahead sufficient: at every point the parser needs to choose a production,
the FIRST sets of the alternatives are disjoint, so `table[nonterminal][token]`
resolves to exactly one rule.

The odd non-terminal names in the grammar (`SimpleExpressionZegond`,
`TermZegond`, `FactorZegond`, plus the `B`, `C`, `D`, `G`, `H` helpers) are the
residue of that transformation. They exist because an expression statement and
an assignment both start with `ID`:

```
x = 1;      /* assignment  */
x + 1;      /* expression  */
```

The parser cannot tell which it is looking at until *after* the `ID` is
consumed. So the grammar splits every expression non-terminal into two variants:
the normal one, and a `Zegond` ("second") variant that assumes the leading `ID`
has already been eaten. `OtherStmt → ID IdStatementPrime` handles the first
case, `SimpleExpressionZegond` the second. It is left factoring applied across
an entire expression hierarchy.

## Grammar

```
1.  Program              → DeclarationList
2.  DeclarationList      → Declaration DeclarationList | ε
3.  Declaration          → DeclarationInitial DeclarationPrime
4.  DeclarationInitial   → TypeSpecifier ID
5.  DeclarationPrime     → FunDeclarationPrime | VarDeclarationPrime
6.  VarDeclarationPrime  → ; | [ NUM ] VarDeclArrayPrime | = Expression ;
7.  VarDeclArrayPrime    → ;
8.  FunDeclarationPrime  → ( Params ) CompoundStmt
9.  TypeSpecifier        → int | void
10. Params               → int ID ParamPrime ParamList | void
11. ParamList            → , Param ParamList | ε
12. Param                → DeclarationInitial ParamPrime
13. ParamPrime           → [ ] | ε
14. CompoundStmt         → { DeclarationList StatementList }
15. StatementList        → Statement StatementList | ε
16. Statement            → if ( Expression ) Statement ElseOpt | OtherStmt
17. ElseOpt              → else Statement | ε
18. OtherStmt            → ID IdStatementPrime | SimpleExpressionZegond ; | ;
                           | CompoundStmt | IterationStmt | ReturnStmt
                           | BreakStmt | GotoStmt | SwitchStmt
19. IdStatementPrime     → : Statement | B ;
20. BreakStmt            → break ;
21. IterationStmt        → while ( Expression ) Statement
22. ReturnStmt           → return ReturnStmtPrime
23. ReturnStmtPrime      → ; | Expression ;
24. Expression           → SimpleExpressionZegond | ID B
25. B                    → = Expression | [ Expression ] H | SimpleExpressionPrime
26. H                    → = Expression | C
27. SimpleExpressionZegond   → AdditiveExpressionZegond C
28. SimpleExpressionPrime    → AdditiveExpressionPrime C
29. C                    → Relop AdditiveExpression | ε
30. Relop                → < | ==
31. AdditiveExpression   → Term D
32. AdditiveExpressionPrime  → TermPrime D
33. AdditiveExpressionZegond → TermZegond D
34. D                    → Addop Term D | ε
35. Addop                → + | -
36. Term                 → SignedFactor G
37. TermPrime            → SignedFactorPrime G
38. TermZegond           → SignedFactorZegond G
39. G                    → Mulop SignedFactor G | ε
40. Mulop                → * | /
41. SignedFactor         → + Factor | - Factor | Factor
42. SignedFactorPrime    → FactorPrime
43. SignedFactorZegond   → + Factor | - Factor | FactorZegond
44. Factor               → ( Expression ) | ID VarCallPrime | NUM
45. VarCallPrime         → ( Args ) | VarPrime
46. VarPrime             → [ Expression ] | ε
47. FactorPrime          → ( Args ) | ε
48. FactorZegond         → ( Expression ) | NUM
49. Args                 → ArgList | ε
50. ArgList              → Expression ArgListPrime
51. ArgListPrime         → , Expression ArgListPrime | ε
52. GotoStmt             → goto ID ;
53. SwitchStmt           → switch ( Expression ) { CaseList DefaultOpt }
54. CaseList             → Case CaseList | ε
55. Case                 → case Constant : StatementList
56. Constant             → NUM
57. DefaultOpt           → default : StatementList | ε
```

## Parse table construction

FIRST and FOLLOW sets are written out explicitly in the source rather than
computed by fixed-point iteration — the grammar never changes, so the sets are
constants and having them spelled out makes the table auditable by hand.

`build_parse_table` then applies the textbook rule for each production
`A → α`:

- for every terminal `a ∈ FIRST(α)`, set `table[A][a] = A → α`
- if `ε ∈ FIRST(α)`, then for every `b ∈ FOLLOW(A)`, set `table[A][b] = A → α`

The result is a `dict` of `dict`s keyed by non-terminal and lookahead token. No
entry is ever written twice, which is the practical confirmation that the
grammar really is LL(1).

## The parsing loop

A stack of `(symbol, tree_node)` pairs, seeded with `$` and `Program`:

```
while stack is not empty:
    top, node = stack.peek()
    if top is a terminal:
        if it matches the lookahead:  attach the lexeme as a leaf, pop, advance
        else:                          missing-terminal error
    else:
        production = table[top][lookahead]
        if found:  pop, create child nodes, push them right-to-left
        else:      illegal-non-terminal error
```

Pushing right-to-left is what makes the leftmost symbol come off the stack
first, so the tree is built top-down, left-to-right — the parse tree *is* the
leftmost derivation, recorded as it happens.

## Error recovery

Panic mode, so that a single mistake does not cascade into dozens of bogus
messages. Three situations arise:

**Missing terminal.** The stack expects a terminal the lookahead is not.
Report `#N : syntax error, missing X`, pop the expectation, and do **not**
consume input — the parser assumes the token was simply left out and carries on
from where it was. The half-built node is detached from the tree, so the
output only ever shows what was actually derived.

**Illegal token.** No table entry exists for the current
`(non-terminal, lookahead)` pair, and the lookahead is not in FOLLOW of that
non-terminal. Report `#N : syntax error, illegal X`, discard the token, and
try again with the same non-terminal still on the stack — flagged as
recovering.

**Synchronising.** No table entry exists, but the lookahead *is* in FOLLOW of
the non-terminal, which means the parser has skipped far enough to be back in a
consistent state. Pop the non-terminal and resume. If this is the first error
at this point, report it as `missing X`; if the parser was already recovering,
the message was issued when the tokens started being discarded, so the node is
closed with `epsilon` and nothing further is reported. EOF is treated as a
synchronising token, which is how truncated input terminates cleanly.

## Output files

The tree is built with [`anytree`](https://pypi.org/project/anytree/), the one
third-party library the assignment allows, and rendered with its `RenderTree`.
Phase 3 drops the dependency by implementing an equivalent `Node` and
`RenderTree` directly in `compiler.py`, so the finished compiler runs on a bare
Python installation.

| File | Content |
| --- | --- |
| `parse_tree.txt` | the tree, one node per line, depth shown by indentation |
| `syntax_errors.txt` | one error per line, or `There is no syntax error.` |

## Tests

24 cases live under `phase2-parser/tests/`, split into `core` (18), `extended`
(3) and `stress` (3). Each holds an `input.txt` together with the `parse_tree.txt` and
`syntax_errors.txt` the parser is expected to produce, so they act as golden
files.

```bash
python3 tools/run_tests.py phase2
```

`phase2-parser/generate_testcases.py` is the small helper used to author some
of those cases: it feeds a program to the parser and snapshots the result into
a new case directory.

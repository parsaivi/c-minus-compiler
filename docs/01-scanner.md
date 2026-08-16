# Phase 1 — Scanner

The scanner turns raw source text into a stream of tokens. It is a hand-written
DFA: no regular-expression engine, no lexer generator, one character of
lookahead and a single left-to-right pass over the input.

Source: [`phase1-scanner/compiler.py`](../phase1-scanner/compiler.py)

## Tokens

| Type | Definition |
| --- | --- |
| `NUM` | `[0-9]+` |
| `ID` | `[A-Za-z][A-Za-z0-9_]*` |
| `KEYWORD` | `if else void int while break return goto switch case default` |
| `SYMBOL` | `; : , [ ] ( ) { } + - * / = < ==` |
| comment | `// … newline` or `/* … */` — consumed, never emitted |
| whitespace | space, `\n`, `\r`, `\t`, `\v`, `\f` — consumed, never emitted |

`==` is the only two-character token, so a single lookahead character is enough
to keep the automaton deterministic: on `=` the scanner peeks once and decides
between `=` and `==`. Every other symbol is decided by the current character
alone.

## Interface

```python
scanner = Scanner(source_text)
token = scanner.get_next_token()   # ('KEYWORD', 'while') … or None at EOF
```

`get_next_token` is the whole public surface. Phase 1 drives it from a loop to
dump `tokens.txt`; from phase 2 onwards the parser pulls tokens from it one at a
time, which is what makes the compiler single-pass — the source is never
buffered into a token list.

Internally `_scan_one_token` dispatches on the current character to
`_scan_number`, `_scan_id_or_keyword`, `_scan_symbol`, or one of the comment
skippers. Comments and whitespace return a `skip` sentinel so the driver loop
keeps going without the caller ever seeing them.

## Error handling

Lexical errors recover by **panic mode**: the offending characters are consumed
until something that can legally start a new token appears, the damaged text is
recorded, and scanning resumes. A malformed token never aborts the run.

| Message | Trigger | Example |
| --- | --- | --- |
| `Invalid input` | a character that cannot begin any token | `@`, `cd!e` |
| `Invalid number` | a digit run glued to letters, or a leading zero | `125d`, `0123` |
| `Unclosed comment` | `/*` with no closing `*/` before EOF | `/* comment 3` |
| `Unmatched comment` | `*/` outside any comment | `*/` |

Two details worth calling out:

- An unclosed comment can swallow the rest of the file, so the recorded lexeme
  is truncated to the first nine characters plus `...` rather than dumping the
  remainder of the source into the error log.
- `\f` (form feed) is whitespace but does **not** increment the line counter,
  while `\n` does. Line numbers drive every error message in all three phases,
  so this is load-bearing.

## Symbol table

A list, pre-loaded with the keywords, appended to the first time each new
identifier is seen. At this stage it holds only lexemes; phase 3 attaches type,
kind, address and arity information to the same conceptual table.

## Output files

Written to the working directory, alongside `input.txt`:

| File | Content |
| --- | --- |
| `tokens.txt` | one line per source line: `N.<TAB>(TYPE, lexeme) …` |
| `lexical_errors.txt` | `N.<TAB>(lexeme, message)`, or `There is no lexical error.` |
| `symbol_table.txt` | numbered list of keywords followed by identifiers |

## Try it

```bash
cd phase1-scanner
cp examples/lexical-errors/input.txt .
python3 compiler.py
cat lexical_errors.txt
```

The bundled example deliberately contains one of every error kind:

```
8.	(3d, Invalid number)
10.	(cd!e, Invalid input)
12.	(*/, Unmatched comment)
16.	(@, Invalid input)
28.	(/* commen..., Unclosed comment)
```

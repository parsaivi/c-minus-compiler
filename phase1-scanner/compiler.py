# Compiler Design - Phase 1 (Scanner)
# Name: Ali Moghadasi, Parsa Malekian
# Student ID: 402106542, 402171075

KEYWORDS = [
    "break",
    "else",
    "for",
    "if",
    "int",
    "return",
    "void",
    "goto",
    "switch",
    "case",
    "default",
    "while",
]

SYMBOLS = {
    ";",
    ":",
    ",",
    "[",
    "]",
    "(",
    ")",
    "{",
    "}",
    "+",
    "-",
    "*",
    "/",
    "=",
    "<",
    "==",
}

WHITESPACE = {" ", "\n", "\r", "\t", "\v", "\f"}


class Scanner:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.lineno = 1
        self.symbol_table = list(KEYWORDS)
        self.errors = []
        self.tokens_by_line = {}
        self._done = False

    def _peek(self, offset=0):
        i = self.pos + offset
        if i >= len(self.text):
            return ""
        return self.text[i]

    def _advance(self, n=1):
        for _ in range(n):
            if self.pos < len(self.text):
                if self.text[self.pos] == "\n":
                    self.lineno += 1
                self.pos += 1

    def _at_end(self):
        return self.pos >= len(self.text)

    def _is_letter(self, ch):
        return ("a" <= ch <= "z") or ("A" <= ch <= "Z")

    def _is_id_char(self, ch):
        return ch.isdigit() or self._is_letter(ch) or ch == "_"

    def _add_token(self, ttype, lexeme):
        line = self.lineno
        if line not in self.tokens_by_line:
            self.tokens_by_line[line] = []
        self.tokens_by_line[line].append((ttype, lexeme))

    def _add_to_symbol_table(self, lexeme):
        if lexeme not in self.symbol_table:
            self.symbol_table.append(lexeme)

    def _record_error(self, lexeme, message, line=None):
        self.errors.append((line if line is not None else self.lineno, lexeme, message))

    def _truncate_unclosed(self, s):
        if len(s) <= 9:
            return s
        return s[:9] + "..."

    def _valid_after_id(self, ch):
        if ch in WHITESPACE:
            return True
        if ch == "/":
            return True
        if ch == "=":
            return True
        if ch in SYMBOLS:
            return True
        return False

    def _is_delimiter(self, ch):
        if ch in WHITESPACE:
            return True
        if ch == "/":
            return True
        if ch == "=":
            return True
        if ch in SYMBOLS:
            return True
        return False

    def _collect_invalid(self):
        start = self.pos
        if self._is_letter(self._peek()):
            while not self._at_end() and self._is_id_char(self._peek()):
                self._advance()
            while not self._at_end() and not self._is_delimiter(self._peek()):
                self._advance()
        else:
            self._advance()

        bad = self.text[start : self.pos]
        self._record_error(bad, "Invalid input")

    def _skip_line_comment(self):
        self._advance(2)
        while not self._at_end() and self._peek() != "\n":
            self._advance()

    def _skip_block_comment(self):
        start = self.pos
        start_line = self.lineno
        self._advance(2)
        while not self._at_end():
            if self._peek() == "*" and self._peek(1) == "/":
                self._advance(2)
                return
            self._advance()
        thrown = self.text[start : self.pos]
        self._record_error(
            self._truncate_unclosed(thrown), "Unclosed comment", line=start_line
        )

    def _skip_whitespace(self):
        while not self._at_end() and self._peek() in WHITESPACE:
            self._advance()

    def _scan_number(self):
        start = self.pos
        while not self._at_end() and self._peek().isdigit():
            self._advance()
        num = self.text[start : self.pos]

        if len(num) > 1 and num[0] == "0":
            while not self._at_end() and self._is_id_char(self._peek()):
                self._advance()
            bad = self.text[start : self.pos]
            self._record_error(bad, "Invalid number")
            return None

        if not self._at_end() and self._is_letter(self._peek()):
            while not self._at_end() and self._is_id_char(self._peek()):
                self._advance()
            bad = self.text[start : self.pos]
            self._record_error(bad, "Invalid number")
            return None

        self._add_token("NUM", num)
        return ("NUM", num)

    def _scan_id_or_keyword(self):
        start = self.pos
        self._advance()
        while not self._at_end() and self._is_id_char(self._peek()):
            self._advance()

        if not self._at_end() and not self._valid_after_id(self._peek()):
            self.pos = start
            self._collect_invalid()
            return None

        lexeme = self.text[start : self.pos]

        if lexeme in KEYWORDS:
            self._add_token("KEYWORD", lexeme)
            return ("KEYWORD", lexeme)

        self._add_to_symbol_table(lexeme)
        self._add_token("ID", lexeme)
        return ("ID", lexeme)

    def _scan_symbol(self):
        ch = self._peek()

        if ch == "=":
            if self._peek(1) == "=":
                self._advance(2)
                self._add_token("SYMBOL", "==")
                return ("SYMBOL", "==")
            self._advance()
            self._add_token("SYMBOL", "=")
            return ("SYMBOL", "=")

        if ch in SYMBOLS:
            self._advance()
            self._add_token("SYMBOL", ch)
            return ("SYMBOL", ch)

        return None

    def _scan_one_token(self):
        self._skip_whitespace()
        if self._at_end():
            return None

        ch = self._peek()

        if ch.isdigit():
            return self._scan_number()

        if self._is_letter(ch):
            return self._scan_id_or_keyword()

        if ch == "*":
            if self._peek(1) == "/":
                self._advance(2)
                self._record_error("*/", "Unmatched comment")
                return None
            self._advance()
            self._add_token("SYMBOL", "*")
            return ("SYMBOL", "*")

        if ch == "/":
            nxt = self._peek(1)
            if nxt == "/":
                self._skip_line_comment()
                return "skip"
            if nxt == "*":
                self._skip_block_comment()
                return "skip"
            self._advance()
            self._add_token("SYMBOL", "/")
            return ("SYMBOL", "/")

        sym = self._scan_symbol()
        if sym:
            return sym

        self._collect_invalid()
        return None

    def get_next_token(self):
        if self._done:
            return None

        while not self._at_end():
            tok = self._scan_one_token()
            if tok == "skip":
                continue
            if tok is not None:
                return tok

        self._done = True
        return None


def format_token(tok):
    ttype, lexeme = tok
    return f"({ttype}, {lexeme})"


def write_tokens(path, tokens_by_line):
    lines_out = []
    for lineno in sorted(tokens_by_line.keys()):
        parts = [format_token(t) for t in tokens_by_line[lineno]]
        lines_out.append(f"{lineno}.\t" + " ".join(parts) + " ")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_out))
        if lines_out:
            f.write("\n")


def write_errors(path, errors):
    with open(path, "w", encoding="utf-8") as f:
        if not errors:
            f.write("There is no lexical error.\n")
        else:
            for lineno, lexeme, msg in errors:
                f.write(f"{lineno}.\t({lexeme}, {msg})\n")


def write_symbol_table(path, table):
    with open(path, "w", encoding="utf-8") as f:
        for i, lexeme in enumerate(table, 1):
            f.write(f"{i}.\t{lexeme}\n")


def main():
    with open("input.txt", "r", encoding="utf-8") as f:
        source = f.read()

    scanner = Scanner(source)

    while True:
        tok = scanner.get_next_token()
        if tok is None:
            break

    write_tokens("tokens.txt", scanner.tokens_by_line)
    write_errors("lexical_errors.txt", scanner.errors)
    write_symbol_table("symbol_table.txt", scanner.symbol_table)


if __name__ == "__main__":
    main()

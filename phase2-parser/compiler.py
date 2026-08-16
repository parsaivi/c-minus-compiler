# Compiler Design - Phase 2 (LL(1) Parser)
# Name: Ali Moghadasi, Parsa Malekian
# Student ID: 402106542, 402171075

from anytree import Node, RenderTree

# ---------------------------------------------------------------------------
# SCANNER
# ---------------------------------------------------------------------------

KEYWORDS = [
    "break",
    "else",
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
        self.current_token_line = 1

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
        return ch.isdigit() or self._is_letter(ch)

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
        else:
            self._advance()

        bad = self.text[start: self.pos]
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
        thrown = self.text[start: self.pos]
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
        num = self.text[start: self.pos]

        if len(num) > 1 and num[0] == "0":
            while not self._at_end() and self._is_id_char(self._peek()):
                self._advance()
            bad = self.text[start: self.pos]
            self._record_error(bad, "Invalid number")
            return None

        if not self._at_end() and self._is_letter(self._peek()):
            while not self._at_end() and self._is_id_char(self._peek()):
                self._advance()
            bad = self.text[start: self.pos]
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

        lexeme = self.text[start: self.pos]

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

    def _scan_one_token_body(self):
        """Scan one token WITHOUT skipping leading whitespace (caller does that)."""
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
        """Return (ttype, lexeme). Returns ('$', '$') at EOF and on all subsequent calls."""
        if self._done:
            self.current_token_line = self.lineno
            return ("$", "$")

        while not self._at_end():
            self._skip_whitespace()
            if self._at_end():
                break
            self.current_token_line = self.lineno
            tok = self._scan_one_token_body()
            if tok == "skip":
                continue
            if tok is not None:
                return tok

        self._done = True
        self.current_token_line = self.lineno + 1
        return ("$", "$")


# ---------------------------------------------------------------------------
# GRAMMAR
# ---------------------------------------------------------------------------

NON_TERMINALS = {
    'Program', 'DeclarationList', 'Declaration', 'DeclarationInitial',
    'DeclarationPrime', 'VarDeclarationPrime', 'VarDeclArrayPrime',
    'FunDeclarationPrime', 'TypeSpecifier', 'Params', 'ParamList',
    'Param', 'ParamPrime', 'CompoundStmt', 'StatementList', 'Statement',
    'ElseOpt', 'OtherStmt', 'IdStatementPrime', 'BreakStmt', 'IterationStmt',
    'ReturnStmt', 'ReturnStmtPrime', 'Expression', 'B', 'H',
    'SimpleExpressionZegond', 'SimpleExpressionPrime', 'C', 'Relop',
    'AdditiveExpression', 'AdditiveExpressionPrime', 'AdditiveExpressionZegond',
    'D', 'Addop', 'Term', 'TermPrime', 'TermZegond', 'G', 'Mulop',
    'SignedFactor', 'SignedFactorPrime', 'SignedFactorZegond', 'Factor',
    'VarCallPrime', 'VarPrime', 'FactorPrime', 'FactorZegond',
    'Args', 'ArgList', 'ArgListPrime', 'GotoStmt', 'SwitchStmt',
    'CaseList', 'Case', 'Constant', 'DefaultOpt',
}

PRODUCTIONS = [
    ('Program',                    ['DeclarationList']),                                         # 0
    ('DeclarationList',            ['Declaration', 'DeclarationList']),                          # 1
    ('DeclarationList',            []),                                                          # 2  ε
    ('Declaration',                ['DeclarationInitial', 'DeclarationPrime']),                  # 3
    ('DeclarationInitial',         ['TypeSpecifier', 'ID']),                                     # 4
    ('DeclarationPrime',           ['FunDeclarationPrime']),                                     # 5
    ('DeclarationPrime',           ['VarDeclarationPrime']),                                     # 6
    ('VarDeclarationPrime',        [';']),                                                       # 7
    ('VarDeclarationPrime',        ['[', 'NUM', ']', 'VarDeclArrayPrime']),                      # 8
    ('VarDeclarationPrime',        ['=', 'Expression', ';']),                                    # 9
    ('VarDeclArrayPrime',          [';']),                                                       # 10
    ('VarDeclArrayPrime',          ['=', 'Expression', ';']),                                    # 11
    ('FunDeclarationPrime',        ['(', 'Params', ')', 'CompoundStmt']),                        # 12
    ('TypeSpecifier',              ['int']),                                                     # 13
    ('TypeSpecifier',              ['void']),                                                    # 14
    ('Params',                     ['int', 'ID', 'ParamPrime', 'ParamList']),                    # 15
    ('Params',                     ['void']),                                                    # 16
    ('ParamList',                  [',', 'Param', 'ParamList']),                                 # 17
    ('ParamList',                  []),                                                          # 18  ε
    ('Param',                      ['DeclarationInitial', 'ParamPrime']),                        # 19
    ('ParamPrime',                 ['[', ']']),                                                  # 20
    ('ParamPrime',                 []),                                                          # 21  ε
    ('CompoundStmt',               ['{', 'DeclarationList', 'StatementList', '}']),              # 22
    ('StatementList',              ['Statement', 'StatementList']),                              # 23
    ('StatementList',              []),                                                          # 24  ε
    ('Statement',                  ['if', '(', 'Expression', ')', 'Statement', 'ElseOpt']),      # 25
    ('Statement',                  ['OtherStmt']),                                               # 26
    ('ElseOpt',                    ['else', 'Statement']),                                       # 27
    ('ElseOpt',                    []),                                                          # 28  ε
    ('OtherStmt',                  ['ID', 'IdStatementPrime']),                                  # 29
    ('OtherStmt',                  ['SimpleExpressionZegond', ';']),                             # 30
    ('OtherStmt',                  [';']),                                                       # 31
    ('OtherStmt',                  ['CompoundStmt']),                                            # 32
    ('OtherStmt',                  ['IterationStmt']),                                           # 33
    ('OtherStmt',                  ['ReturnStmt']),                                              # 34
    ('OtherStmt',                  ['BreakStmt']),                                               # 35
    ('OtherStmt',                  ['GotoStmt']),                                                # 36
    ('OtherStmt',                  ['SwitchStmt']),                                              # 37
    ('IdStatementPrime',           [':', 'Statement']),                                          # 38
    ('IdStatementPrime',           ['B', ';']),                                                  # 39
    ('BreakStmt',                  ['break', ';']),                                              # 40
    ('IterationStmt',              ['while', '(', 'Expression', ')', 'Statement']),              # 41
    ('ReturnStmt',                 ['return', 'ReturnStmtPrime']),                               # 42
    ('ReturnStmtPrime',            [';']),                                                       # 43
    ('ReturnStmtPrime',            ['Expression', ';']),                                         # 44
    ('Expression',                 ['SimpleExpressionZegond']),                                  # 45
    ('Expression',                 ['ID', 'B']),                                                 # 46
    ('B',                          ['=', 'Expression']),                                         # 47
    ('B',                          ['[', 'Expression', ']', 'H']),                               # 48
    ('B',                          ['SimpleExpressionPrime']),                                   # 49
    ('H',                          ['=', 'Expression']),                                         # 50
    ('H',                          ['G', 'D', 'C']),                                             # 51  fixed: was ['C']
    ('SimpleExpressionZegond',     ['AdditiveExpressionZegond', 'C']),                           # 52
    ('SimpleExpressionPrime',      ['AdditiveExpressionPrime', 'C']),                            # 53
    ('C',                          ['Relop', 'AdditiveExpression']),                             # 54
    ('C',                          []),                                                          # 55  ε
    ('Relop',                      ['<']),                                                       # 56
    ('Relop',                      ['==']),                                                      # 57
    ('AdditiveExpression',         ['Term', 'D']),                                               # 58
    ('AdditiveExpressionPrime',    ['TermPrime', 'D']),                                          # 59
    ('AdditiveExpressionZegond',   ['TermZegond', 'D']),                                         # 60
    ('D',                          ['Addop', 'Term', 'D']),                                      # 61
    ('D',                          []),                                                          # 62  ε
    ('Addop',                      ['+']),                                                       # 63
    ('Addop',                      ['-']),                                                       # 64
    ('Term',                       ['SignedFactor', 'G']),                                       # 65
    ('TermPrime',                  ['SignedFactorPrime', 'G']),                                  # 66
    ('TermZegond',                 ['SignedFactorZegond', 'G']),                                 # 67
    ('G',                          ['Mulop', 'SignedFactor', 'G']),                              # 68
    ('G',                          []),                                                          # 69  ε
    ('Mulop',                      ['*']),                                                       # 70
    ('Mulop',                      ['/']),                                                       # 71
    ('SignedFactor',               ['+', 'Factor']),                                             # 72
    ('SignedFactor',               ['-', 'Factor']),                                             # 73
    ('SignedFactor',               ['Factor']),                                                  # 74
    ('SignedFactorPrime',          ['FactorPrime']),                                             # 75
    ('SignedFactorZegond',         ['+', 'Factor']),                                             # 76
    ('SignedFactorZegond',         ['-', 'Factor']),                                             # 77
    ('SignedFactorZegond',         ['FactorZegond']),                                            # 78
    ('Factor',                     ['(', 'Expression', ')']),                                    # 79
    ('Factor',                     ['ID', 'VarCallPrime']),                                      # 80
    ('Factor',                     ['NUM']),                                                     # 81
    ('VarCallPrime',               ['(', 'Args', ')']),                                          # 82
    ('VarCallPrime',               ['VarPrime']),                                                # 83
    ('VarPrime',                   ['[', 'Expression', ']']),                                    # 84
    ('VarPrime',                   []),                                                          # 85  ε
    ('FactorPrime',                ['(', 'Args', ')']),                                          # 86
    ('FactorPrime',                []),                                                          # 87  ε
    ('FactorZegond',               ['(', 'Expression', ')']),                                    # 88
    ('FactorZegond',               ['NUM']),                                                     # 89
    ('Args',                       ['ArgList']),                                                 # 90
    ('Args',                       []),                                                          # 91  ε
    ('ArgList',                    ['Expression', 'ArgListPrime']),                              # 92
    ('ArgListPrime',               [',', 'Expression', 'ArgListPrime']),                         # 93
    ('ArgListPrime',               []),                                                          # 94  ε
    ('GotoStmt',                   ['goto', 'ID', ';']),                                         # 95
    ('SwitchStmt',                 ['switch', '(', 'Expression', ')', '{', 'CaseList', 'DefaultOpt', '}']),  # 96
    ('CaseList',                   ['Case', 'CaseList']),                                        # 97
    ('CaseList',                   []),                                                          # 98  ε
    ('Case',                       ['case', 'Constant', ':', 'StatementList']),                  # 99
    ('Constant',                   ['NUM']),                                                     # 100
    ('DefaultOpt',                 ['default', ':', 'StatementList']),                           # 101
    ('DefaultOpt',                 []),                                                          # 102 ε
]

# ---------------------------------------------------------------------------
# FIRST and FOLLOW SETS
# ---------------------------------------------------------------------------

NT_FIRST = {
    'Program':                  {'int', 'void', 'ε'},
    'DeclarationList':          {'int', 'void', 'ε'},
    'Declaration':              {'int', 'void'},
    'DeclarationInitial':       {'int', 'void'},
    'DeclarationPrime':         {'(', ';', '[', '='},
    'VarDeclarationPrime':      {';', '[', '='},
    'VarDeclArrayPrime':        {';', '='},
    'FunDeclarationPrime':      {'('},
    'TypeSpecifier':            {'int', 'void'},
    'Params':                   {'int', 'void'},
    'ParamList':                {',', 'ε'},
    'Param':                    {'int', 'void'},
    'ParamPrime':               {'[', 'ε'},
    'CompoundStmt':             {'{'},
    'StatementList':            {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', 'ε'},
    'Statement':                {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch'},
    'ElseOpt':                  {'else', 'ε'},
    'OtherStmt':                {'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch'},
    'IdStatementPrime':         {':', '=', '[', '(', '*', '/', '+', '-', '<', '=='},
    'BreakStmt':                {'break'},
    'IterationStmt':            {'while'},
    'ReturnStmt':               {'return'},
    'ReturnStmtPrime':          {';', '+', '-', '(', 'NUM', 'ID'},
    'Expression':               {'+', '-', '(', 'NUM', 'ID'},
    'B':                        {'=', '[', '(', '*', '/', '+', '-', '<', '==', 'ε'},
    'H':                        {'=', '*', '/', '+', '-', '<', '==', 'ε'},
    'SimpleExpressionZegond':   {'+', '-', '(', 'NUM'},
    'SimpleExpressionPrime':    {'(', '*', '/', '+', '-', '<', '==', 'ε'},
    'C':                        {'<', '==', 'ε'},
    'Relop':                    {'<', '=='},
    'AdditiveExpression':       {'+', '-', '(', 'NUM', 'ID'},
    'AdditiveExpressionPrime':  {'(', '*', '/', '+', '-', 'ε'},
    'AdditiveExpressionZegond': {'+', '-', '(', 'NUM'},
    'D':                        {'+', '-', 'ε'},
    'Addop':                    {'+', '-'},
    'Term':                     {'+', '-', '(', 'NUM', 'ID'},
    'TermPrime':                {'(', '*', '/', 'ε'},
    'TermZegond':               {'+', '-', '(', 'NUM'},
    'G':                        {'*', '/', 'ε'},
    'Mulop':                    {'*', '/'},
    'SignedFactor':             {'+', '-', '(', 'NUM', 'ID'},
    'SignedFactorPrime':        {'(', 'ε'},
    'SignedFactorZegond':       {'+', '-', '(', 'NUM'},
    'Factor':                   {'(', 'NUM', 'ID'},
    'VarCallPrime':             {'(', '[', 'ε'},
    'VarPrime':                 {'[', 'ε'},
    'FactorPrime':              {'(', 'ε'},
    'FactorZegond':             {'(', 'NUM'},
    'Args':                     {'+', '-', '(', 'NUM', 'ID', 'ε'},
    'ArgList':                  {'+', '-', '(', 'NUM', 'ID'},
    'ArgListPrime':             {',', 'ε'},
    'GotoStmt':                 {'goto'},
    'SwitchStmt':               {'switch'},
    'CaseList':                 {'case', 'ε'},
    'Case':                     {'case'},
    'Constant':                 {'NUM'},
    'DefaultOpt':               {'default', 'ε'},
}

NT_FOLLOW = {
    'Program':                  {'$'},
    'DeclarationList':          {'$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'Declaration':              {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'DeclarationInitial':       {'(', ';', '[', '=', ',', ')'},
    'DeclarationPrime':         {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'VarDeclarationPrime':      {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'VarDeclArrayPrime':        {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'FunDeclarationPrime':      {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}'},
    'TypeSpecifier':            {'ID'},
    'Params':                   {')'},
    'ParamList':                {')'},
    'Param':                    {',', ')'},
    'ParamPrime':               {',', ')'},
    'CompoundStmt':             {'int', 'void', '$', 'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'StatementList':            {'}', 'case', 'default'},
    'Statement':                {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'ElseOpt':                  {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'OtherStmt':                {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'IdStatementPrime':         {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'BreakStmt':                {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'IterationStmt':            {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'ReturnStmt':               {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'ReturnStmtPrime':          {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'Expression':               {';', ')', ']', ','},
    'B':                        {';', ')', ']', ','},
    'H':                        {';', ')', ']', ','},
    'SimpleExpressionZegond':   {';', ')', ']', ','},
    'SimpleExpressionPrime':    {';', ')', ']', ','},
    'C':                        {';', ')', ']', ','},
    'Relop':                    {'+', '-', '(', 'NUM', 'ID'},
    'AdditiveExpression':       {';', ')', ']', ','},
    'AdditiveExpressionPrime':  {';', ')', ']', ',', '<', '=='},
    'AdditiveExpressionZegond': {';', ')', ']', ','},
    'D':                        {';', ')', ']', ',', '<', '=='},
    'Addop':                    {'+', '-', '(', 'NUM', 'ID'},
    'Term':                     {'+', '-', ';', ')', ']', ','},
    'TermPrime':                {'+', '-', ';', ')', ']', ',', '<', '=='},
    'TermZegond':               {'+', '-', ';', ')', ']', ','},
    'G':                        {'+', '-', ';', ')', ']', ',', '<', '=='},
    'Mulop':                    {'+', '-', '(', 'NUM', 'ID'},
    'SignedFactor':             {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'SignedFactorPrime':        {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'SignedFactorZegond':       {'*', '/', '+', '-', ';', ')', ']', ','},
    'Factor':                   {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'VarCallPrime':             {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'VarPrime':                 {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'FactorPrime':              {'*', '/', '+', '-', ';', ')', ']', ',', '<', '=='},
    'FactorZegond':             {'*', '/', '+', '-', ';', ')', ']', ','},
    'Args':                     {')'},
    'ArgList':                  {')'},
    'ArgListPrime':             {')'},
    'GotoStmt':                 {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'SwitchStmt':               {'if', 'ID', '+', '-', '(', 'NUM', ';', '{', 'while', 'return', 'break', 'goto', 'switch', '}', 'else', 'case', 'default'},
    'CaseList':                 {'default', '}'},
    'Case':                     {'case', 'default', '}'},
    'Constant':                 {':'},
    'DefaultOpt':               {'}'},
}

# ---------------------------------------------------------------------------
# PARSE TABLE
# ---------------------------------------------------------------------------

def first_of_sequence(seq):
    """Compute FIRST of a sequence of grammar symbols."""
    result = set()
    for sym in seq:
        if sym not in NON_TERMINALS:  # terminal
            result.add(sym)
            return result
        f = NT_FIRST[sym]
        result |= (f - {'ε'})
        if 'ε' not in f:
            return result
    result.add('ε')
    return result


def build_parse_table():
    table = {nt: {} for nt in NON_TERMINALS}
    for i, (nt, prod) in enumerate(PRODUCTIONS):
        first = first_of_sequence(prod)
        for t in first - {'ε'}:
            if t not in table[nt]:
                table[nt][t] = i
        if 'ε' in first:
            for t in NT_FOLLOW[nt]:
                if t not in table[nt]:
                    table[nt][t] = i
    return table


PARSE_TABLE = build_parse_table()

# ---------------------------------------------------------------------------
# PARSE TREE OUTPUT
# ---------------------------------------------------------------------------

def write_parse_tree(path, root):
    lines = []
    for pre, fill, node in RenderTree(root):
        lines.append(f"{pre}{node.name}")
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))
        if lines:
            f.write('\n')


def write_syntax_errors(path, errors):
    with open(path, 'w', encoding='utf-8') as f:
        if not errors:
            f.write('There is no syntax error.\n')
        else:
            for lineno, msg in errors:
                f.write(f'#{lineno} : {msg}\n')

# ---------------------------------------------------------------------------
# PARSER
# ---------------------------------------------------------------------------

def token_key(tok):
    """Return the lookup key for a token in the parse table."""
    ttype, lexeme = tok
    if ttype in ('ID', 'NUM', '$'):
        return ttype
    return lexeme


class Parser:
    def __init__(self, scanner):
        self.scanner = scanner
        self.errors = []
        self.current_token = None

    def _advance(self):
        self.current_token = self.scanner.get_next_token()

    def _line(self):
        return self.scanner.current_token_line

    def parse(self):
        root = Node('Program')
        self._advance()
        stack = [('$', None, False), ('Program', root, False)]

        while stack:
            top_sym, top_node, recovering = stack[-1]
            key = token_key(self.current_token)

            if top_sym == '$':
                stack.pop()
                break

            if top_sym not in NON_TERMINALS:
                if key == top_sym:
                    ttype, lexeme = self.current_token
                    if ttype == '$':
                        top_node.name = '$'
                    else:
                        top_node.name = f'({ttype}, {lexeme}) '
                    stack.pop()
                    self._advance()
                else:
                    self.errors.append((self._line(), f'syntax error, missing {top_sym}'))
                    top_node.parent = None
                    stack.pop()
            else:
                prod_idx = PARSE_TABLE.get(top_sym, {}).get(key)
                if prod_idx is not None:
                    _, prod = PRODUCTIONS[prod_idx]
                    stack.pop()
                    if not prod:
                        Node('epsilon', parent=top_node)
                    else:
                        children = []
                        for sym in prod:
                            child = Node(sym, parent=top_node)
                            children.append(child)
                        for sym, child in reversed(list(zip(prod, children))):
                            stack.append((sym, child, False))
                else:
                    follow = NT_FOLLOW.get(top_sym, set())
                    if key == '$':
                        self.errors.append((self._line(), f'syntax error, missing {top_sym}'))
                        top_node.parent = None
                        stack.pop()
                    elif key in follow:
                        if not recovering:
                            self.errors.append((self._line(), f'syntax error, missing {top_sym}'))
                            top_node.parent = None
                        else:
                            Node('epsilon', parent=top_node)
                        stack.pop()
                    else:
                        self.errors.append((self._line(), f'syntax error, illegal {key}'))
                        stack[-1] = (top_sym, top_node, True)
                        self._advance()

        Node('$', parent=root)
        return root

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    with open('input.txt', 'r', encoding='utf-8') as f:
        source = f.read()

    scanner = Scanner(source)
    parser = Parser(scanner)
    root = parser.parse()

    write_parse_tree('parse_tree.txt', root)
    write_syntax_errors('syntax_errors.txt', parser.errors)


if __name__ == '__main__':
    main()

# Compiler Design - Phase 3 (Intermediate Code Generator)
# Name: Ali Moghadasi, Parsa Malekian
# Student ID: 402106542, 402171075

class Node:
    def __init__(self, name, parent=None):
        self.name = name
        self._parent = None
        self.children = []
        if parent is not None:
            self.parent = parent

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        if self._parent is not None and self in self._parent.children:
            self._parent.children.remove(self)
        self._parent = value
        if value is not None and self not in value.children:
            value.children.append(self)


def RenderTree(root):
    def _walk(node, prefix="", is_last=True, is_root=True):
        if is_root:
            yield "", node
            for i, child in enumerate(node.children):
                yield from _walk(child, "", i == len(node.children) - 1, False)
            return
        connector = "└── " if is_last else "├── "
        yield prefix + connector, node
        extension = "    " if is_last else "│   "
        for i, child in enumerate(node.children):
            yield from _walk(child, prefix + extension, i == len(node.children) - 1, False)

    for pre, node in _walk(root):
        yield pre, None, node

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
                        top_node.lineno = self._line()
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
# CODE GENERATOR + SEMANTIC ANALYSER (Phase 3, including optional parts)
# ---------------------------------------------------------------------------

class Tmp:
    """Temporary storage: absolute address (globals/init) or FP-relative offset."""

    def __init__(self, abs_addr=None, fp_off=None):
        self.abs_addr = abs_addr
        self.fp_off = fp_off

    @property
    def is_fp(self):
        return self.fp_off is not None


class Symbol:
    def __init__(self, name, kind, typ, address, size=1, params=None, on_stack=False):
        self.name = name
        self.kind = kind  # 'var', 'array', 'func', 'param', 'array_param'
        self.typ = typ    # 'int', 'void'
        self.address = address  # absolute address OR FP offset
        self.size = size
        self.params = params or []
        self.on_stack = on_stack
        self.code_start = None
        self.frame_size = 0
        self.temp_base = 0
        self.return_address = None
        self.return_value = None


class CodeGenerator:
    """One-pass semantic analysis + TAC generation with FP-relative temps (recursion-safe)."""

    ADDR_SP = 4
    ADDR_FP = 8
    ADDR_RET = 12
    STACK_BASE = 20000
    DATA_START = 100
    MAX_TEMPS = 96
    SCRATCH_LO = 16
    SCRATCH_HI = 96  # inclusive upper bound for scratch addresses

    def __init__(self):
        self.pb = []
        self.data_ptr = self.DATA_START
        self.global_scope = {}
        self.local_scope = None
        self.current_func = None
        self.functions = {}
        self.labels = {}
        self.goto_fixups = []
        self.break_stack = []
        self.while_depth = 0
        self.switch_depth = 0
        self.semantic_errors = []
        self.emitting = True
        self.fp_temp_count = 0
        self.fp_temp_floor = 0
        self.scratch_ptr = self.SCRATCH_LO

        self.functions['output'] = Symbol(
            'output', 'func', 'void', None,
            params=[Symbol('a', 'param', 'int', None)]
        )

    # ---- emit / allocate ----

    def emit(self, op, a1='', a2='', a3=''):
        if not self.emitting:
            return -1
        self.pb.append([op, str(a1), str(a2), str(a3)])
        return len(self.pb) - 1

    def i(self):
        return len(self.pb)

    def allocate(self, words=1):
        addr = self.data_ptr
        self.data_ptr += 4 * words
        return addr

    def _alloc_scratch(self):
        addr = self.scratch_ptr
        self.scratch_ptr += 4
        if self.scratch_ptr > self.SCRATCH_HI:
            self.scratch_ptr = self.SCRATCH_LO
        return addr

    def new_temp(self):
        if self.current_func is not None:
            off = self.current_func.temp_base + self.fp_temp_count * 4
            self.fp_temp_count += 1
            return Tmp(fp_off=off)
        return Tmp(abs_addr=self.allocate(1))

    def reset_temps(self):
        self.fp_temp_count = self.fp_temp_floor

    def src_op(self, x):
        """Convert Tmp|str to a TAC source operand."""
        if isinstance(x, Tmp):
            if x.abs_addr is not None:
                return str(x.abs_addr)
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_FP), f'#{x.fp_off}', str(sc))
            return f'@{sc}'
        return str(x)

    def dst_op(self, x):
        """Convert Tmp|str to a TAC destination operand."""
        if isinstance(x, Tmp):
            if x.abs_addr is not None:
                return str(x.abs_addr)
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_FP), f'#{x.fp_off}', str(sc))
            return f'@{sc}'
        return str(x)

    def emit_assign(self, src, dst):
        s = self.src_op(src)
        d = self.dst_op(dst)
        return self.emit('ASSIGN', s, d, '')

    def emit_binop(self, op, a, b, dst):
        sa = self.src_op(a)
        sb = self.src_op(b)
        dd = self.dst_op(dst)
        return self.emit(op, sa, sb, dd)

    def emit_jp(self, target):
        return self.emit('JP', str(target), '', '')

    def emit_jpf(self, cond, target):
        return self.emit('JPF', self.src_op(cond), str(target), '')

    def emit_print(self, val):
        return self.emit('PRINT', self.src_op(val), '', '')

    def lookup(self, name):
        if self.local_scope is not None and name in self.local_scope:
            return self.local_scope[name]
        if name in self.global_scope:
            return self.global_scope[name]
        if name in self.functions:
            return self.functions[name]
        return None

    def error(self, lineno, message):
        self.semantic_errors.append((lineno, message))

    def has_semantic_errors(self):
        return len(self.semantic_errors) > 0

    def write_output(self, path='output.txt'):
        with open(path, 'w', encoding='utf-8') as f:
            if self.has_semantic_errors():
                f.write('The output code has not been generated.\n')
            else:
                for idx, (op, a1, a2, a3) in enumerate(self.pb):
                    f.write(f"{idx}\t({op}, {a1}, {a2}, {a3})\n")

    def write_semantic_errors(self, path='semantic_errors.txt'):
        with open(path, 'w', encoding='utf-8') as f:
            if not self.semantic_errors:
                f.write('The input program is semantically correct.\n')
            else:
                for lineno, msg in self.semantic_errors:
                    f.write(f'#{lineno} : {msg}\n')

    # ---- tree helpers ----

    @staticmethod
    def is_terminal(node):
        n = node.name
        return n.startswith('(') or n == 'epsilon' or n == '$'

    @staticmethod
    def lexeme(node):
        name = node.name.strip()
        if name.startswith('(') and name.endswith(')'):
            inner = name[1:-1]
            comma = inner.find(',')
            if comma >= 0:
                return inner[comma + 1:].strip()
        return name

    @staticmethod
    def token_type(node):
        name = node.name.strip()
        if name.startswith('(') and ',' in name:
            return name[1:name.find(',')].strip()
        return None

    def lineno_of(self, node, default=1):
        if node is None:
            return default
        if hasattr(node, 'lineno') and node.lineno is not None:
            return node.lineno
        for c in getattr(node, 'children', []) or []:
            ln = self.lineno_of(c, None)
            if ln is not None:
                return ln
        return default

    def child_nt(self, node, name):
        for c in node.children:
            if c.name == name:
                return c
        return None

    def children_nt(self, node, name):
        return [c for c in node.children if c.name == name]

    def first_terminal(self, node, ttype=None):
        for c in node.children:
            if self.is_terminal(c) and c.name != 'epsilon':
                if ttype is None or self.token_type(c) == ttype:
                    return c
        return None

    def _is_empty_nt(self, node):
        if node is None:
            return True
        return len(node.children) == 1 and node.children[0].name == 'epsilon'

    # ---- stack address helpers ----

    def addr_cell(self, sym):
        """Return operand locating sym's cell.
        For stack symbols returns a Tmp holding the absolute address (indirect).
        For globals returns absolute address string (direct).
        """
        if not sym.on_stack:
            return str(sym.address), False
        t = self.new_temp()
        self.emit_binop('ADD', str(self.ADDR_FP), f'#{sym.address}', t)
        return t, True

    def load_sym(self, sym):
        """Load symbol value into a fresh Tmp (FP-relative inside functions)."""
        v = self.new_temp()
        if not sym.on_stack:
            self.emit_assign(str(sym.address), v)
            return v
        sc = self._alloc_scratch()
        self.emit('ADD', str(self.ADDR_FP), f'#{sym.address}', str(sc))
        self.emit_assign(f'@{sc}', v)
        return v

    def load_at(self, addr):
        """Materialize mem[addr] into a fresh Tmp. addr is Tmp|str holding an address."""
        v = self.new_temp()
        sc = self._alloc_scratch()
        self.emit_assign(addr, Tmp(abs_addr=sc))
        self.emit_assign(f'@{sc}', v)
        return v

    def store_sym(self, sym, value):
        if not sym.on_stack:
            self.emit_assign(value, str(sym.address))
        else:
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_FP), f'#{sym.address}', str(sc))
            self.emit_assign(value, f'@{sc}')

    def init_runtime(self):
        self.emit('ASSIGN', f'#{self.STACK_BASE}', str(self.ADDR_SP), '')
        self.emit('ASSIGN', f'#{self.STACK_BASE}', str(self.ADDR_FP), '')

    # ---- entry ----

    def generate(self, root):
        self.init_runtime()
        self.gen_program(root)
        for idx, label in self.goto_fixups:
            if label in self.labels and idx >= 0:
                self.pb[idx][1] = str(self.labels[label])
        if self.has_semantic_errors():
            self.pb = []
            self.emitting = False

    def gen_program(self, node):
        decl_list = self.child_nt(node, 'DeclarationList')
        if decl_list:
            self.gen_declaration_list(decl_list, global_scope=True)

    def gen_declaration_list(self, node, global_scope=True):
        if not node or self._is_empty_nt(node):
            return
        decl = self.child_nt(node, 'Declaration')
        rest = self.child_nt(node, 'DeclarationList')
        if decl:
            self.gen_declaration(decl, global_scope=global_scope)
        if rest:
            self.gen_declaration_list(rest, global_scope=global_scope)

    def gen_declaration(self, node, global_scope=True):
        init = self.child_nt(node, 'DeclarationInitial')
        prime = self.child_nt(node, 'DeclarationPrime')
        typ, name, id_node = self.gen_declaration_initial(init)
        fun = self.child_nt(prime, 'FunDeclarationPrime')
        var = self.child_nt(prime, 'VarDeclarationPrime')
        if fun:
            self.gen_fun_declaration(fun, typ, name, id_node)
        elif var:
            self.gen_var_declaration(var, typ, name, id_node, global_scope=global_scope)

    def gen_declaration_initial(self, node):
        ts = self.child_nt(node, 'TypeSpecifier')
        typ = self.lexeme(self.first_terminal(ts))
        id_node = self.first_terminal(node, 'ID')
        name = self.lexeme(id_node)
        return typ, name, id_node

    def gen_var_declaration(self, node, typ, name, id_node, global_scope=True):
        lineno = self.lineno_of(id_node)
        if typ == 'void':
            self.error(lineno, f"Semantic Error! Illegal type of void for '{name}'.")

        num_node = None
        for c in node.children:
            if self.token_type(c) == 'NUM':
                num_node = c
                break

        has_assign = any(
            self.token_type(c) == 'SYMBOL' and self.lexeme(c) == '='
            for c in node.children
        )
        expr = self.child_nt(node, 'Expression')
        arr_prime = self.child_nt(node, 'VarDeclArrayPrime')
        if arr_prime:
            expr = self.child_nt(arr_prime, 'Expression') or expr
            has_assign = has_assign or any(
                self.token_type(c) == 'SYMBOL' and self.lexeme(c) == '='
                for c in arr_prime.children
            )

        scope = self.global_scope if global_scope else self.local_scope
        is_array = num_node is not None
        size = int(self.lexeme(num_node)) if is_array else 1
        kind = 'array' if is_array else 'var'

        if global_scope:
            addr = self.allocate(size)
            sym = Symbol(name, kind, 'int' if typ != 'void' else 'void', addr,
                         size=size, on_stack=False)
            scope[name] = sym
            for i in range(size):
                self.emit('ASSIGN', '#0', str(addr + 4 * i), '')
            if has_assign and expr:
                val, _ = self.gen_expression(expr)
                self.emit_assign(val, str(addr))
        else:
            sym = scope.get(name)
            if sym is None:
                off = self.current_func.temp_base  # shouldn't happen after pre-scan
                sym = Symbol(name, kind, 'int' if typ != 'void' else 'void', off,
                             size=size, on_stack=True)
                scope[name] = sym
            for i in range(size):
                sc = self._alloc_scratch()
                self.emit('ADD', str(self.ADDR_FP), f'#{sym.address + 4 * i}', str(sc))
                self.emit('ASSIGN', '#0', f'@{sc}', '')
            if has_assign and expr:
                val, _ = self.gen_expression(expr)
                self.store_sym(sym, val)

    def _assign_local_offsets(self, decl_list, offset):
        if not decl_list or self._is_empty_nt(decl_list):
            return offset
        decl = self.child_nt(decl_list, 'Declaration')
        rest = self.child_nt(decl_list, 'DeclarationList')
        if decl:
            init = self.child_nt(decl, 'DeclarationInitial')
            prime = self.child_nt(decl, 'DeclarationPrime')
            typ, name, id_node = self.gen_declaration_initial(init)
            var = self.child_nt(prime, 'VarDeclarationPrime') if prime else None
            if var:
                if typ == 'void':
                    self.error(self.lineno_of(id_node),
                               f"Semantic Error! Illegal type of void for '{name}'.")
                num_node = None
                for c in var.children:
                    if self.token_type(c) == 'NUM':
                        num_node = c
                        break
                size = int(self.lexeme(num_node)) if num_node else 1
                kind = 'array' if num_node else 'var'
                sym = Symbol(name, kind, 'int' if typ != 'void' else 'void',
                             offset, size=size, on_stack=True)
                self.local_scope[name] = sym
                offset += 4 * size
        if rest:
            offset = self._assign_local_offsets(rest, offset)
        return offset

    def gen_fun_declaration(self, node, typ, name, id_node):
        # Skip this function's body so later global inits still run.
        skip_jp = None
        if name != 'main':
            skip_jp = self.emit('JP', '0', '', '')

        self.local_scope = {}
        self.labels = {}
        self.goto_fixups = []
        self.fp_temp_count = 0
        self.fp_temp_floor = 0

        params_node = self.child_nt(node, 'Params')
        # Frame: 0=RA, 4=RV, 8=saved_FP, then params, then locals, then temps
        offset = 12
        params = self.gen_params(params_node, offset)
        offset = 12 + 4 * len(params)

        compound = self.child_nt(node, 'CompoundStmt')
        decls = self.child_nt(compound, 'DeclarationList') if compound else None
        offset = self._assign_local_offsets(decls, offset)
        temp_base = offset
        frame_size = temp_base + self.MAX_TEMPS * 4

        sym = Symbol(name, 'func', typ, None, params=params)
        sym.temp_base = temp_base
        sym.frame_size = frame_size
        sym.code_start = self.i()
        self.functions[name] = sym
        self.current_func = sym

        # prologue for main (never called via gen_call)
        if name == 'main':
            self.emit('ASSIGN', str(self.ADDR_SP), str(self.ADDR_FP), '')
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_SP), f'#{frame_size}', str(sc))
            self.emit('ASSIGN', str(sc), str(self.ADDR_SP), '')

        if compound:
            self._gen_local_inits(decls)
            stmts = self.child_nt(compound, 'StatementList')
            if stmts:
                self.gen_statement_list(stmts)

        if name != 'main':
            self._emit_return()

        for idx, label in self.goto_fixups:
            if label in self.labels and idx >= 0:
                self.pb[idx][1] = str(self.labels[label])
        self.goto_fixups = []
        self.labels = {}
        self.local_scope = None
        self.current_func = None
        self.fp_temp_count = 0
        self.fp_temp_floor = 0
        if skip_jp is not None and skip_jp >= 0:
            self.pb[skip_jp][1] = str(self.i())

    def _gen_local_inits(self, decl_list):
        if not decl_list or self._is_empty_nt(decl_list):
            return
        self.reset_temps()
        decl = self.child_nt(decl_list, 'Declaration')
        rest = self.child_nt(decl_list, 'DeclarationList')
        if decl:
            init = self.child_nt(decl, 'DeclarationInitial')
            prime = self.child_nt(decl, 'DeclarationPrime')
            typ, name, id_node = self.gen_declaration_initial(init)
            var = self.child_nt(prime, 'VarDeclarationPrime') if prime else None
            if var:
                sym = self.local_scope.get(name)
                num_node = None
                for c in var.children:
                    if self.token_type(c) == 'NUM':
                        num_node = c
                        break
                size = int(self.lexeme(num_node)) if num_node else 1
                for i in range(size):
                    sc = self._alloc_scratch()
                    self.emit('ADD', str(self.ADDR_FP), f'#{sym.address + 4 * i}', str(sc))
                    self.emit('ASSIGN', '#0', f'@{sc}', '')
                has_assign = any(
                    self.token_type(c) == 'SYMBOL' and self.lexeme(c) == '='
                    for c in var.children
                )
                expr = self.child_nt(var, 'Expression')
                arr_prime = self.child_nt(var, 'VarDeclArrayPrime')
                if arr_prime:
                    expr = self.child_nt(arr_prime, 'Expression') or expr
                    has_assign = has_assign or any(
                        self.token_type(c) == 'SYMBOL' and self.lexeme(c) == '='
                        for c in arr_prime.children
                    )
                if has_assign and expr:
                    val, _ = self.gen_expression(expr)
                    self.store_sym(sym, val)
        if rest:
            self._gen_local_inits(rest)

    def gen_params(self, node, offset):
        params = []
        if not node:
            return params
        terminals = [c for c in node.children if self.is_terminal(c) and c.name != 'epsilon']
        if len(terminals) == 1 and self.lexeme(terminals[0]) == 'void':
            return params

        id_node = self.first_terminal(node, 'ID')
        if id_node is None:
            return params
        pname = self.lexeme(id_node)
        pprime = self.child_nt(node, 'ParamPrime')
        is_array = pprime is not None and any(
            self.lexeme(c) == '[' for c in pprime.children if self.is_terminal(c)
        )
        kind = 'array_param' if is_array else 'param'
        sym = Symbol(pname, kind, 'int', offset, on_stack=True)
        self.local_scope[pname] = sym
        params.append(sym)
        offset += 4

        plist = self.child_nt(node, 'ParamList')
        more, _ = self.gen_param_list(plist, offset)
        params.extend(more)
        return params

    def gen_param_list(self, node, offset):
        params = []
        if not node or self._is_empty_nt(node):
            return params, offset
        param = self.child_nt(node, 'Param')
        rest = self.child_nt(node, 'ParamList')
        if param:
            p, offset = self.gen_param(param, offset)
            params.append(p)
        if rest:
            more, offset = self.gen_param_list(rest, offset)
            params.extend(more)
        return params, offset

    def gen_param(self, node, offset):
        init = self.child_nt(node, 'DeclarationInitial')
        typ, name, id_node = self.gen_declaration_initial(init)
        pprime = self.child_nt(node, 'ParamPrime')
        is_array = pprime is not None and any(
            self.lexeme(c) == '[' for c in pprime.children if self.is_terminal(c)
        )
        kind = 'array_param' if is_array else 'param'
        sym = Symbol(name, kind, typ if typ != 'void' else 'int', offset, on_stack=True)
        self.local_scope[name] = sym
        return sym, offset + 4

    def gen_compound_stmt(self, node):
        stmts = self.child_nt(node, 'StatementList')
        decls = self.child_nt(node, 'DeclarationList')
        if decls and not self._is_empty_nt(decls):
            self.gen_declaration_list(decls, global_scope=False)
        if stmts:
            self.gen_statement_list(stmts)

    def gen_statement_list(self, node):
        if not node or self._is_empty_nt(node):
            return
        stmt = self.child_nt(node, 'Statement')
        rest = self.child_nt(node, 'StatementList')
        if stmt:
            self.gen_statement(stmt)
        if rest:
            self.gen_statement_list(rest)

    def gen_statement(self, node):
        self.reset_temps()
        if any(self.lexeme(c) == 'if' for c in node.children if self.is_terminal(c)):
            expr = self.child_nt(node, 'Expression')
            stmts = self.children_nt(node, 'Statement')
            else_opt = self.child_nt(node, 'ElseOpt')
            cond, _ = self.gen_expression(expr)
            jpf = self.emit_jpf(cond, '0')
            self.gen_statement(stmts[0])
            has_else = else_opt and any(
                self.lexeme(c) == 'else' for c in else_opt.children if self.is_terminal(c)
            )
            if has_else:
                jp = self.emit('JP', '0', '', '')
                if jpf >= 0:
                    self.pb[jpf][2] = str(self.i())
                else_stmt = self.child_nt(else_opt, 'Statement')
                self.gen_statement(else_stmt)
                if jp >= 0:
                    self.pb[jp][1] = str(self.i())
            else:
                if jpf >= 0:
                    self.pb[jpf][2] = str(self.i())
            return
        other = self.child_nt(node, 'OtherStmt')
        if other:
            self.gen_other_stmt(other)

    def gen_other_stmt(self, node):
        if self.child_nt(node, 'CompoundStmt'):
            self.gen_compound_stmt(self.child_nt(node, 'CompoundStmt'))
            return
        if self.child_nt(node, 'IterationStmt'):
            self.gen_iteration_stmt(self.child_nt(node, 'IterationStmt'))
            return
        if self.child_nt(node, 'ReturnStmt'):
            self.gen_return_stmt(self.child_nt(node, 'ReturnStmt'))
            return
        if self.child_nt(node, 'BreakStmt'):
            self.gen_break_stmt(self.child_nt(node, 'BreakStmt'))
            return
        if self.child_nt(node, 'GotoStmt'):
            self.gen_goto_stmt(self.child_nt(node, 'GotoStmt'))
            return
        if self.child_nt(node, 'SwitchStmt'):
            self.gen_switch_stmt(self.child_nt(node, 'SwitchStmt'))
            return

        id_node = self.first_terminal(node, 'ID')
        id_prime = self.child_nt(node, 'IdStatementPrime')
        if id_node and id_prime:
            if any(self.lexeme(c) == ':' for c in id_prime.children if self.is_terminal(c)):
                label = self.lexeme(id_node)
                self.labels[label] = self.i()
                stmt = self.child_nt(id_prime, 'Statement')
                if stmt:
                    self.gen_statement(stmt)
            else:
                b = self.child_nt(id_prime, 'B')
                self.gen_id_b(id_node, b)
            return

        sez = self.child_nt(node, 'SimpleExpressionZegond')
        if sez:
            self.gen_simple_expression_zegond(sez)

    def gen_iteration_stmt(self, node):
        loop_start = self.i()
        self.reset_temps()
        expr = self.child_nt(node, 'Expression')
        cond, _ = self.gen_expression(expr)
        jpf = self.emit_jpf(cond, '0')
        self.break_stack.append([])
        self.while_depth += 1
        stmt = self.child_nt(node, 'Statement')
        self.gen_statement(stmt)
        self.while_depth -= 1
        self.emit('JP', str(loop_start), '', '')
        end = self.i()
        if jpf >= 0:
            self.pb[jpf][2] = str(end)
        for bi in self.break_stack.pop():
            if bi >= 0:
                self.pb[bi][1] = str(end)

    def gen_break_stmt(self, node):
        lineno = self.lineno_of(node)
        if self.while_depth == 0 and self.switch_depth == 0:
            self.error(lineno, "Semantic Error! No 'while' found for 'break'.")
        if self.break_stack:
            idx = self.emit('JP', '0', '', '')
            self.break_stack[-1].append(idx)

    def gen_goto_stmt(self, node):
        id_node = self.first_terminal(node, 'ID')
        label = self.lexeme(id_node)
        if label in self.labels:
            self.emit('JP', str(self.labels[label]), '', '')
        else:
            idx = self.emit('JP', '0', '', '')
            self.goto_fixups.append((idx, label))

    def _emit_return(self, value=None):
        """Return from current non-main function via runtime stack."""
        if value is not None:
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_FP), '#4', str(sc))
            self.emit_assign(value, f'@{sc}')

        # Keep a copy of FP in a scratch (absolute) — must survive SP/FP updates
        fp_save = self._alloc_scratch()
        self.emit('ASSIGN', str(self.ADDR_FP), str(fp_save), '')

        ra_addr = self._alloc_scratch()
        self.emit('ADD', str(fp_save), '#0', str(ra_addr))
        self.emit('ASSIGN', f'@{ra_addr}', str(self.ADDR_RET), '')

        sfp_addr = self._alloc_scratch()
        self.emit('ADD', str(fp_save), '#8', str(sfp_addr))

        self.emit('ASSIGN', str(self.ADDR_FP), str(self.ADDR_SP), '')
        self.emit('ASSIGN', f'@{sfp_addr}', str(self.ADDR_FP), '')
        self.emit('JP', f'@{self.ADDR_RET}', '', '')

    def gen_return_stmt(self, node):
        prime = self.child_nt(node, 'ReturnStmtPrime')
        expr = self.child_nt(prime, 'Expression') if prime else None
        val = None
        if expr:
            val, _ = self.gen_expression(expr)
        if self.current_func and self.current_func.name != 'main':
            self._emit_return(val)
        elif val is not None and self.current_func:
            pass

    def gen_switch_stmt(self, node):
        expr = self.child_nt(node, 'Expression')
        switch_val, _ = self.gen_expression(expr)
        # Pin switch_val so case checks / bodies don't reuse its temp slot
        if isinstance(switch_val, Tmp) and switch_val.is_fp:
            self.fp_temp_floor = max(self.fp_temp_floor, self.fp_temp_count)

        self.break_stack.append([])
        self.switch_depth += 1

        case_list = self.child_nt(node, 'CaseList')
        default_opt = self.child_nt(node, 'DefaultOpt')
        cases = []
        self.collect_cases(case_list, cases)

        has_default = default_opt and any(
            self.lexeme(c) == 'default' for c in default_opt.children if self.is_terminal(c)
        )

        body_starts = []
        fallthrough_jps = []
        next_check_jpf = None

        for case_node, const_val in cases:
            if next_check_jpf is not None and next_check_jpf >= 0:
                self.pb[next_check_jpf][2] = str(self.i())
            self.reset_temps()
            # ensure we don't reuse switch_val slot
            if self.fp_temp_count < self.fp_temp_floor:
                self.fp_temp_count = self.fp_temp_floor
            temp = self.new_temp()
            self.emit_binop('EQ', switch_val, f'#{const_val}', temp)
            next_check_jpf = self.emit_jpf(temp, '0')
            body_starts.append(self.i())
            stmts = self.child_nt(case_node, 'StatementList')
            if stmts:
                self.gen_statement_list(stmts)
            fallthrough_jps.append(self.emit('JP', '0', '', ''))

        default_start = None
        if has_default:
            default_start = self.i()
            if next_check_jpf is not None and next_check_jpf >= 0:
                self.pb[next_check_jpf][2] = str(default_start)
            dstmts = self.child_nt(default_opt, 'StatementList')
            if dstmts:
                self.gen_statement_list(dstmts)
        end = self.i()
        if not has_default and next_check_jpf is not None and next_check_jpf >= 0:
            self.pb[next_check_jpf][2] = str(end)

        for i in range(len(fallthrough_jps) - 1):
            if fallthrough_jps[i] >= 0:
                self.pb[fallthrough_jps[i]][1] = str(body_starts[i + 1])
        if fallthrough_jps and fallthrough_jps[-1] >= 0:
            self.pb[fallthrough_jps[-1]][1] = str(default_start if has_default else end)

        self.switch_depth -= 1
        self.fp_temp_floor = 0
        for bi in self.break_stack.pop():
            if bi >= 0:
                self.pb[bi][1] = str(end)

    def collect_cases(self, node, out):
        if not node or self._is_empty_nt(node):
            return
        case = self.child_nt(node, 'Case')
        rest = self.child_nt(node, 'CaseList')
        if case:
            const = self.child_nt(case, 'Constant')
            num = self.first_terminal(const, 'NUM') if const else self.first_terminal(case, 'NUM')
            out.append((case, int(self.lexeme(num))))
        if rest:
            self.collect_cases(rest, out)

    # ---- expressions: return (operand, type) where operand is Tmp or '#n' ----

    def gen_expression(self, node):
        sez = self.child_nt(node, 'SimpleExpressionZegond')
        if sez:
            return self.gen_simple_expression_zegond(sez)
        id_node = self.first_terminal(node, 'ID')
        b = self.child_nt(node, 'B')
        return self.gen_id_b(id_node, b)

    def check_binop_types(self, left_t, right_t, lineno):
        """Both operands of arithmetic/relop must be int."""
        ok = True
        if left_t not in ('int', 'unknown'):
            self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {left_t} instead of int.")
            ok = False
        elif right_t not in ('int', 'unknown'):
            self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {right_t} instead of int.")
            ok = False
        return ok

    def check_unary_type(self, typ, lineno):
        if typ not in ('int', 'unknown'):
            self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {typ} instead of int.")
            return False
        return True

    def check_assign_types(self, lhs_t, rhs_t, lineno):
        if lhs_t in ('unknown',) or rhs_t in ('unknown',):
            return
        if lhs_t != rhs_t:
            # match judge expected: Got <lhs> instead of <rhs>
            self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {lhs_t} instead of {rhs_t}.")

    def gen_id_b(self, id_node, b):
        name = self.lexeme(id_node)
        lineno = self.lineno_of(id_node)

        if b is None:
            return self._use_id(name, lineno)

        # assignment: B -> = Expression
        if any(self.lexeme(c) == '=' for c in b.children if self.is_terminal(c)) and \
           self.child_nt(b, 'Expression') and not self.child_nt(b, 'H') and \
           not any(self.lexeme(c) == '[' for c in b.children if self.is_terminal(c)):
            expr = self.child_nt(b, 'Expression')
            val, rhs_t = self.gen_expression(expr)
            sym = self.lookup(name)
            if sym is None:
                self.error(lineno, f"Semantic Error! '{name}' is not defined.")
                return '#0', 'int'
            if sym.kind in ('func',):
                self.error(lineno, f"Semantic Error! '{name}' is not defined.")
                return '#0', 'int'
            lhs_t = 'array' if sym.kind in ('array', 'array_param') else 'int'
            self.check_assign_types(lhs_t, rhs_t, lineno)
            self.store_sym(sym, val)
            return self.load_sym(sym), lhs_t

        # array: B -> [ Expression ] H
        if any(self.lexeme(c) == '[' for c in b.children if self.is_terminal(c)):
            sym = self.lookup(name)
            idx_expr = self.child_nt(b, 'Expression')
            if sym is None:
                self.error(lineno, f"Semantic Error! '{name}' is not defined.")
                if idx_expr:
                    self.gen_expression(idx_expr)
                return '#0', 'int'
            if sym.kind not in ('array', 'array_param'):
                self.error(lineno, "Semantic Error! Type mismatch in operands, Got int instead of array.")
            idx, idx_t = self.gen_expression(idx_expr)
            if idx_t not in ('int', 'unknown'):
                self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {idx_t} instead of int.")
            addr_temp = self.gen_array_address(name, idx)
            h = self.child_nt(b, 'H')
            return self.gen_h(addr_temp, h)

        sep = self.child_nt(b, 'SimpleExpressionPrime')
        if sep:
            return self.gen_simple_expression_prime(name, sep, lineno)

        return self._use_id(name, lineno)

    def _use_id(self, name, lineno):
        sym = self.lookup(name)
        if sym is None:
            self.error(lineno, f"Semantic Error! '{name}' is not defined.")
            return '#0', 'unknown'
        if sym.kind == 'func':
            self.error(lineno, f"Semantic Error! '{name}' is not defined.")
            return '#0', 'unknown'
        if sym.kind in ('array', 'array_param'):
            return self.load_sym(sym), 'array'
        return self.load_sym(sym), 'int'

    def gen_h(self, addr_temp, h):
        if h is None:
            return self.load_at(addr_temp), 'int'
        if any(self.lexeme(c) == '=' for c in h.children if self.is_terminal(c)) and \
           self.child_nt(h, 'Expression'):
            expr = self.child_nt(h, 'Expression')
            val, _ = self.gen_expression(expr)
            # store val at *addr_temp
            sc = self._alloc_scratch()
            self.emit_assign(addr_temp, Tmp(abs_addr=sc))
            self.emit_assign(val, f'@{sc}')
            return self.load_at(addr_temp), 'int'
        val = self.load_at(addr_temp)
        g = self.child_nt(h, 'G')
        d = self.child_nt(h, 'D')
        c = self.child_nt(h, 'C')
        val, t = self.apply_g(val, 'int', g)
        val, t = self.apply_d(val, t, d)
        val, t = self.apply_c(val, t, c)
        return val, t

    def gen_array_address(self, name, index_operand):
        sym = self.lookup(name)
        offset = self.new_temp()
        self.emit_binop('MULT', index_operand, '#4', offset)
        result = self.new_temp()
        if sym is None:
            self.emit_binop('ADD', '#0', offset, result)
            return result
        if sym.kind == 'array_param':
            base = self.load_sym(sym)
            self.emit_binop('ADD', base, offset, result)
        elif sym.on_stack:
            base_addr = self.new_temp()
            self.emit_binop('ADD', str(self.ADDR_FP), f'#{sym.address}', base_addr)
            self.emit_binop('ADD', base_addr, offset, result)
        else:
            self.emit_binop('ADD', f'#{sym.address}', offset, result)
        return result

    def gen_simple_expression_zegond(self, node):
        aez = self.child_nt(node, 'AdditiveExpressionZegond')
        c = self.child_nt(node, 'C')
        val, t = self.gen_additive_expression_zegond(aez)
        return self.apply_c(val, t, c)

    def gen_simple_expression_prime(self, name, node, lineno):
        aep = self.child_nt(node, 'AdditiveExpressionPrime')
        c = self.child_nt(node, 'C')
        val, t = self.gen_additive_expression_prime(name, aep, lineno)
        return self.apply_c(val, t, c)

    def gen_additive_expression_zegond(self, node):
        tz = self.child_nt(node, 'TermZegond')
        d = self.child_nt(node, 'D')
        val, t = self.gen_term_zegond(tz)
        return self.apply_d(val, t, d)

    def gen_additive_expression_prime(self, name, node, lineno):
        tp = self.child_nt(node, 'TermPrime')
        d = self.child_nt(node, 'D')
        val, t = self.gen_term_prime(name, tp, lineno)
        return self.apply_d(val, t, d)

    def gen_additive_expression(self, node):
        term = self.child_nt(node, 'Term')
        d = self.child_nt(node, 'D')
        val, t = self.gen_term(term)
        return self.apply_d(val, t, d)

    def apply_d(self, left, left_t, d):
        while d and not self._is_empty_nt(d):
            addop = self.child_nt(d, 'Addop')
            term = self.child_nt(d, 'Term')
            op_node = self.first_terminal(addop)
            op = self.lexeme(op_node)
            right, right_t = self.gen_term(term)
            self.check_binop_types(left_t, right_t, self.lineno_of(op_node))
            temp = self.new_temp()
            if op == '+':
                self.emit_binop('ADD', left, right, temp)
            else:
                self.emit_binop('SUB', left, right, temp)
            left, left_t = temp, 'int'
            d = self.child_nt(d, 'D')
        return left, left_t

    def apply_c(self, left, left_t, c):
        if not c or self._is_empty_nt(c):
            return left, left_t
        relop = self.child_nt(c, 'Relop')
        ae = self.child_nt(c, 'AdditiveExpression')
        op_node = self.first_terminal(relop)
        op = self.lexeme(op_node)
        right, right_t = self.gen_additive_expression(ae)
        self.check_binop_types(left_t, right_t, self.lineno_of(op_node))
        temp = self.new_temp()
        if op == '<':
            self.emit_binop('LT', left, right, temp)
        else:
            self.emit_binop('EQ', left, right, temp)
        return temp, 'int'

    def gen_term_zegond(self, node):
        sfz = self.child_nt(node, 'SignedFactorZegond')
        g = self.child_nt(node, 'G')
        val, t = self.gen_signed_factor_zegond(sfz)
        return self.apply_g(val, t, g)

    def gen_term_prime(self, name, node, lineno):
        sfp = self.child_nt(node, 'SignedFactorPrime')
        g = self.child_nt(node, 'G')
        val, t = self.gen_signed_factor_prime(name, sfp, lineno)
        return self.apply_g(val, t, g)

    def gen_term(self, node):
        sf = self.child_nt(node, 'SignedFactor')
        g = self.child_nt(node, 'G')
        val, t = self.gen_signed_factor(sf)
        return self.apply_g(val, t, g)

    def apply_g(self, left, left_t, g):
        while g and not self._is_empty_nt(g):
            mulop = self.child_nt(g, 'Mulop')
            sf = self.child_nt(g, 'SignedFactor')
            op_node = self.first_terminal(mulop)
            op = self.lexeme(op_node)
            right, right_t = self.gen_signed_factor(sf)
            self.check_binop_types(left_t, right_t, self.lineno_of(op_node))
            temp = self.new_temp()
            if op == '*':
                self.emit_binop('MULT', left, right, temp)
            else:
                self.emit_binop('DIV', left, right, temp)
            left, left_t = temp, 'int'
            g = self.child_nt(g, 'G')
        return left, left_t

    def _is_imm(self, val):
        return isinstance(val, str) and val.startswith('#')

    def gen_signed_factor_zegond(self, node):
        if any(self.lexeme(c) == '-' for c in node.children if self.is_terminal(c)):
            minus = next(c for c in node.children if self.is_terminal(c) and self.lexeme(c) == '-')
            val, t = self.gen_factor(self.child_nt(node, 'Factor'))
            self.check_unary_type(t, self.lineno_of(minus))
            if self._is_imm(val) and not val.startswith('#-'):
                return f'#-{val[1:]}', 'int'
            temp = self.new_temp()
            self.emit_binop('SUB', '#0', val, temp)
            return temp, 'int'
        if any(self.lexeme(c) == '+' for c in node.children if self.is_terminal(c)):
            plus = next(c for c in node.children if self.is_terminal(c) and self.lexeme(c) == '+')
            val, t = self.gen_factor(self.child_nt(node, 'Factor'))
            self.check_unary_type(t, self.lineno_of(plus))
            return val, 'int'
        return self.gen_factor_zegond(self.child_nt(node, 'FactorZegond'))

    def gen_signed_factor_prime(self, name, node, lineno):
        fp = self.child_nt(node, 'FactorPrime')
        return self.gen_factor_prime(name, fp, lineno)

    def gen_signed_factor(self, node):
        if any(self.lexeme(c) == '-' for c in node.children if self.is_terminal(c)):
            minus = next(c for c in node.children if self.is_terminal(c) and self.lexeme(c) == '-')
            val, t = self.gen_factor(self.child_nt(node, 'Factor'))
            self.check_unary_type(t, self.lineno_of(minus))
            if self._is_imm(val) and not val.startswith('#-'):
                return f'#-{val[1:]}', 'int'
            temp = self.new_temp()
            self.emit_binop('SUB', '#0', val, temp)
            return temp, 'int'
        if any(self.lexeme(c) == '+' for c in node.children if self.is_terminal(c)):
            plus = next(c for c in node.children if self.is_terminal(c) and self.lexeme(c) == '+')
            val, t = self.gen_factor(self.child_nt(node, 'Factor'))
            self.check_unary_type(t, self.lineno_of(plus))
            return val, 'int'
        return self.gen_factor(self.child_nt(node, 'Factor'))

    def gen_factor_zegond(self, node):
        expr = self.child_nt(node, 'Expression')
        if expr:
            return self.gen_expression(expr)
        num = self.first_terminal(node, 'NUM')
        return f'#{self.lexeme(num)}', 'int'

    def gen_factor(self, node):
        expr = self.child_nt(node, 'Expression')
        if expr:
            return self.gen_expression(expr)
        num = self.first_terminal(node, 'NUM')
        if num:
            return f'#{self.lexeme(num)}', 'int'
        id_node = self.first_terminal(node, 'ID')
        vcp = self.child_nt(node, 'VarCallPrime')
        return self.gen_var_call_prime(self.lexeme(id_node), vcp, self.lineno_of(id_node))

    def gen_factor_prime(self, name, node, lineno):
        if not node or self._is_empty_nt(node):
            return self._use_id(name, lineno)
        args = self.child_nt(node, 'Args')
        return self.gen_call(name, args, lineno)

    def gen_var_call_prime(self, name, node, lineno):
        if node and any(self.lexeme(c) == '(' for c in node.children if self.is_terminal(c)):
            args = self.child_nt(node, 'Args')
            return self.gen_call(name, args, lineno)
        vp = self.child_nt(node, 'VarPrime') if node else None
        return self.gen_var_prime(name, vp, lineno)

    def gen_var_prime(self, name, node, lineno):
        if not node or self._is_empty_nt(node):
            return self._use_id(name, lineno)
        expr = self.child_nt(node, 'Expression')
        if expr:
            sym = self.lookup(name)
            if sym is None:
                self.error(lineno, f"Semantic Error! '{name}' is not defined.")
                self.gen_expression(expr)
                return '#0', 'int'
            if sym.kind not in ('array', 'array_param'):
                self.error(lineno, "Semantic Error! Type mismatch in operands, Got int instead of array.")
            idx, idx_t = self.gen_expression(expr)
            if idx_t not in ('int', 'unknown'):
                self.error(lineno, f"Semantic Error! Type mismatch in operands, Got {idx_t} instead of int.")
            addr = self.gen_array_address(name, idx)
            return self.load_at(addr), 'int'
        return self._use_id(name, lineno)

    def gen_call(self, name, args_node, lineno):
        if name == 'output':
            arg_vals = self.collect_args(args_node)
            if len(arg_vals) != 1:
                self.error(lineno, f"Semantic Error! Mismatch in numbers of arguments of '{name}'.")
            elif arg_vals:
                val, typ = arg_vals[0]
                if typ not in ('int', 'unknown'):
                    self.error(
                        lineno,
                        f"Semantic Error! Mismatch in type of argument 1 of '{name}'. "
                        f"Expected 'int' but got '{typ}' instead."
                    )
                self.emit_print(val)
            return '#0', 'void'

        func = self.functions.get(name)
        if func is None or func.kind != 'func':
            self.error(lineno, f"Semantic Error! '{name}' is not defined.")
            self.collect_args(args_node)
            return '#0', 'unknown'

        arg_vals = self.collect_args(args_node)
        n_params = len(func.params)
        if len(arg_vals) != n_params:
            self.error(lineno, f"Semantic Error! Mismatch in numbers of arguments of '{name}'.")

        for i, ((aval, atyp), param) in enumerate(zip(arg_vals, func.params)):
            expected = 'array' if param.kind == 'array_param' else 'int'
            got = atyp if atyp in ('int', 'array', 'void') else 'int'
            if expected != got and atyp != 'unknown':
                self.error(
                    lineno,
                    f"Semantic Error! Mismatch in type of argument {i + 1} of '{name}'. "
                    f"Expected '{expected}' but got '{got}' instead."
                )

        # --- runtime stack call sequence ---
        for i, ((aval, atyp), param) in enumerate(zip(arg_vals, func.params)):
            sc = self._alloc_scratch()
            self.emit('ADD', str(self.ADDR_SP), f'#{12 + 4 * i}', str(sc))
            self.emit_assign(aval, f'@{sc}')

        # saved FP at SP+8
        sc = self._alloc_scratch()
        self.emit('ADD', str(self.ADDR_SP), '#8', str(sc))
        self.emit('ASSIGN', str(self.ADDR_FP), f'@{sc}', '')

        # RA at SP+0 (backpatched)
        sc_ra = self._alloc_scratch()
        self.emit('ADD', str(self.ADDR_SP), '#0', str(sc_ra))
        ra_idx = self.emit('ASSIGN', '#0', f'@{sc_ra}', '')

        # FP = SP; SP = SP + frame_size (use scratch — FP already points at callee)
        self.emit('ASSIGN', str(self.ADDR_SP), str(self.ADDR_FP), '')
        sc = self._alloc_scratch()
        self.emit('ADD', str(self.ADDR_SP), f'#{func.frame_size}', str(sc))
        self.emit('ASSIGN', str(sc), str(self.ADDR_SP), '')

        self.emit('JP', str(func.code_start), '', '')
        ret_point = self.i()
        if ra_idx >= 0:
            self.pb[ra_idx][1] = f'#{ret_point}'

        if func.typ == 'void':
            return '#0', 'void'

        # RV at SP+4 (callee frame still at SP after return)
        sc = self._alloc_scratch()
        self.emit('ADD', str(self.ADDR_SP), '#4', str(sc))
        rv = self.new_temp()
        self.emit_assign(f'@{sc}', rv)
        return rv, 'int'

    def collect_args(self, node):
        if not node or self._is_empty_nt(node):
            return []
        arg_list = self.child_nt(node, 'ArgList')
        if not arg_list:
            return []
        return self.collect_arg_list(arg_list)

    def collect_arg_list(self, node):
        vals = []
        expr = self.child_nt(node, 'Expression')
        if expr:
            vals.append(self.gen_arg_expression(expr))
        prime = self.child_nt(node, 'ArgListPrime')
        vals.extend(self.collect_arg_list_prime(prime))
        return vals

    def collect_arg_list_prime(self, node):
        if not node or self._is_empty_nt(node):
            return []
        vals = []
        expr = self.child_nt(node, 'Expression')
        if expr:
            vals.append(self.gen_arg_expression(expr))
        prime = self.child_nt(node, 'ArgListPrime')
        vals.extend(self.collect_arg_list_prime(prime))
        return vals

    def _array_base_operand(self, sym):
        """Return operand for an array's base address (for passing array args)."""
        if sym.on_stack:
            t = self.new_temp()
            self.emit_binop('ADD', str(self.ADDR_FP), f'#{sym.address}', t)
            return t, 'array'
        return f'#{sym.address}', 'array'

    def gen_arg_expression(self, node):
        """Like gen_expression, but bare array name passes its base address."""
        id_node = self.first_terminal(node, 'ID')
        b = self.child_nt(node, 'B')
        sez = self.child_nt(node, 'SimpleExpressionZegond')
        if sez:
            return self.gen_simple_expression_zegond(sez)
        if id_node and b is not None:
            name = self.lexeme(id_node)
            sym = self.lookup(name)
            sep = self.child_nt(b, 'SimpleExpressionPrime')
            is_bare = sep is not None and not any(
                self.lexeme(c) == '=' or self.lexeme(c) == '['
                for c in b.children if self.is_terminal(c)
            )
            if is_bare and sym and sym.kind == 'array':
                aep = self.child_nt(sep, 'AdditiveExpressionPrime')
                if aep:
                    tp = self.child_nt(aep, 'TermPrime')
                    d = self.child_nt(aep, 'D')
                    c = self.child_nt(sep, 'C')
                    if self._is_empty_nt(d) and self._is_empty_nt(c) and tp:
                        sfp = self.child_nt(tp, 'SignedFactorPrime')
                        g = self.child_nt(tp, 'G')
                        if self._is_empty_nt(g) and sfp:
                            fp = self.child_nt(sfp, 'FactorPrime')
                            if self._is_empty_nt(fp):
                                return self._array_base_operand(sym)
            return self.gen_id_b(id_node, b)
        if id_node:
            name = self.lexeme(id_node)
            sym = self.lookup(name)
            if sym and sym.kind == 'array':
                return self._array_base_operand(sym)
            return self._use_id(name, self.lineno_of(id_node))
        return self.gen_expression(node)


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

    codegen = CodeGenerator()
    codegen.generate(root)
    codegen.write_output('output.txt')
    codegen.write_semantic_errors('semantic_errors.txt')


if __name__ == '__main__':
    main()

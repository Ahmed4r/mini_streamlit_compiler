"""
Mini Compiler Front-End  ·  CS 404 — Compiler Design
Pharos University in Alexandria
Lexical Analyzer + Syntax Analyzer + Semantic Analysis + Parse Tree
"""

import re
import streamlit as st
import pandas as pd
from dataclasses import dataclass, field

# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mini Compiler · CS 404",
    page_icon="⬡",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# TOKEN TYPES
# ─────────────────────────────────────────────────────────────
TOKEN_KEYWORD = "KEYWORD"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_NUMBER = "NUMBER"
TOKEN_OPERATOR = "OPERATOR"
TOKEN_SYMBOL = "SYMBOL"
TOKEN_STRING = "STRING"
TOKEN_CHAR = "CHAR"
TOKEN_BOOL = "BOOL_LIT"
TOKEN_UNKNOWN = "UNKNOWN"

# ─────────────────────────────────────────────────────────────
# KEYWORDS
# ─────────────────────────────────────────────────────────────
KEYWORDS = {
    "int",
    "float",
    "double",
    "char",
    "bool",
    "long",
    "short",
    "void",
    "string",
    "String",
    "true",
    "false",
}

DECL_TYPES = {
    "int",
    "float",
    "double",
    "char",
    "bool",
    "long",
    "short",
    "void",
    "string",
    "String",
}

BOOL_LITERALS = {"true", "false"}

# ─────────────────────────────────────────────────────────────
# COLORS
# ─────────────────────────────────────────────────────────────
NODE_COLORS = {
    "structural": ("#1e3a5f", "#93c5fd"),
    "keyword": ("#4a1942", "#f0abfc"),
    "identifier": ("#14532d", "#86efac"),
    "number": ("#312e81", "#c4b5fd"),
    "operator": ("#78350f", "#fcd34d"),
    "symbol": ("#334155", "#cbd5e1"),
    "string": ("#064e3b", "#6ee7b7"),
    "char": ("#0f766e", "#99f6e4"),
    "bool": ("#854d0e", "#fde68a"),
    "error": ("#7f1d1d", "#fca5a5"),
    "default": ("#1e293b", "#e2e8f0"),
}

# ─────────────────────────────────────────────────────────────
# SAMPLE CODE
# ─────────────────────────────────────────────────────────────
SAMPLE_CODE = """int x = 5;
float y = 3.2;
char c = 'A';
string name = "Ali";
bool flag = true;

x = x + 10;
"""


# ─────────────────────────────────────────────────────────────
# TREE NODE
# ─────────────────────────────────────────────────────────────
@dataclass
class TreeNode:
    nid: str
    label: str
    category: str = "default"
    children: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
# TREE → DOT
# ─────────────────────────────────────────────────────────────
def tree_to_dot(root):

    lines = [
        "digraph ParseTree {",
        'graph [rankdir=TB, bgcolor="transparent"];',
        'node [shape=box, style="rounded,filled"];',
    ]

    def walk(node):

        fill, font = NODE_COLORS.get(node.category, NODE_COLORS["default"])

        label = node.label.replace('"', '\\"')

        lines.append(
            f'{node.nid} [label="{label}", fillcolor="{fill}", fontcolor="{font}"];'
        )

        for child in node.children:
            lines.append(f"{node.nid} -> {child.nid};")
            walk(child)

    walk(root)

    lines.append("}")

    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# LEXER
# ─────────────────────────────────────────────────────────────
class Lexer:

    def __init__(self, source):

        self.source = source
        self.tokens = []
        self.errors = []

        self.kw_regex = (
            r"\b(?:" + "|".join(sorted(KEYWORDS, key=len, reverse=True)) + r")\b"
        )

    def tokenize(self):

        self.tokens.clear()
        self.errors.clear()

        token_spec = [
            ("STRING_LIT", r'"[^"]*"'),
            ("CHAR_LIT", r"'[^']{1}'"),
            ("FLOAT_NUM", r"\d+\.\d+"),
            ("INT_NUM", r"\d+"),
            ("KEYWORD", self.kw_regex),
            ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("OP", r"==|!=|<=|>=|&&|\|\||[=+\-*/<>!]"),
            ("SYM", r"[;(){}[\],.]"),
            ("COMMENT", r"//[^\n]*"),
            ("SKIP", r"[ \t]+"),
            ("NEWLINE", r"\n"),
            ("MISMATCH", r"."),
        ]

        pattern = "|".join(f"(?P<{name}>{regex})" for name, regex in token_spec)

        line_num = 1

        for mo in re.finditer(pattern, self.source):

            kind = mo.lastgroup
            value = mo.group()

            if kind in ("SKIP", "COMMENT"):
                continue

            elif kind == "NEWLINE":
                line_num += 1
                continue

            elif kind == "MISMATCH":

                self.errors.append(f"Line {line_num}: Unexpected character '{value}'")

                self.tokens.append((value, TOKEN_UNKNOWN, line_num))

            elif kind == "STRING_LIT":

                self.tokens.append((value, TOKEN_STRING, line_num))

            elif kind == "CHAR_LIT":

                self.tokens.append((value, TOKEN_CHAR, line_num))

            elif kind in ("FLOAT_NUM", "INT_NUM"):

                self.tokens.append((value, TOKEN_NUMBER, line_num))

            elif kind == "KEYWORD":

                if value in BOOL_LITERALS:

                    self.tokens.append((value, TOKEN_BOOL, line_num))

                else:

                    self.tokens.append((value, TOKEN_KEYWORD, line_num))

            elif kind == "IDENT":

                self.tokens.append((value, TOKEN_IDENTIFIER, line_num))

            elif kind == "OP":

                self.tokens.append((value, TOKEN_OPERATOR, line_num))

            elif kind == "SYM":

                self.tokens.append((value, TOKEN_SYMBOL, line_num))

        return self.tokens


# ─────────────────────────────────────────────────────────────
# PARSER
# ─────────────────────────────────────────────────────────────
class Parser:

    def __init__(self, tokens):

        self.tokens = [(v, t) for v, t, _ in tokens]

        self.pos = 0

        self.results = []
        self.errors = []

        self.tree = None

        self._nid = 0

        # SYMBOL TABLE
        self.symbol_table = {}

    # ─────────────────────────────────────────────────────────
    # TREE HELPERS
    # ─────────────────────────────────────────────────────────
    def _node(self, label, category="default", children=None):

        self._nid += 1

        return TreeNode(
            f"n{self._nid}",
            label,
            category,
            children or [],
        )

    def _leaf(self, value, token_type):

        cat_map = {
            TOKEN_KEYWORD: "keyword",
            TOKEN_IDENTIFIER: "identifier",
            TOKEN_NUMBER: "number",
            TOKEN_OPERATOR: "operator",
            TOKEN_SYMBOL: "symbol",
            TOKEN_STRING: "string",
            TOKEN_CHAR: "char",
            TOKEN_BOOL: "bool",
            TOKEN_UNKNOWN: "error",
        }

        return self._node(
            f"{value}\n({token_type})", cat_map.get(token_type, "default")
        )

    # ─────────────────────────────────────────────────────────
    # TOKEN HELPERS
    # ─────────────────────────────────────────────────────────
    def _peek(self):

        if self.pos < len(self.tokens):
            return self.tokens[self.pos]

        return None

    def _advance(self):

        tok = self.tokens[self.pos]

        self.pos += 1

        return tok

    def _expect(self, value=None, kind=None):

        tok = self._peek()

        if not tok:
            return None

        v, k = tok

        if (value is None or v == value) and (kind is None or k == kind):
            return self._advance()

        return None

    # ─────────────────────────────────────────────────────────
    # SEMANTIC TYPE CHECK
    # ─────────────────────────────────────────────────────────
    def _is_type_compatible(self, decl_type, expr_node):

        try:
            term_node = expr_node.children[0]
            leaf = term_node.children[0]

            label = leaf.label

        except:
            return False

        # NUMBER
        if "(NUMBER)" in label:

            return decl_type in {
                "int",
                "float",
                "double",
                "long",
                "short",
            }

        # STRING
        if "(STRING)" in label:

            return decl_type in {
                "string",
                "String",
            }

        # CHAR
        if "(CHAR)" in label:

            return decl_type == "char"

        # BOOL
        if "(BOOL_LIT)" in label:

            return decl_type == "bool"

        # IDENTIFIER
        if "(IDENTIFIER)" in label:

            var_name = label.split("\n")[0]

            # undeclared variable
            if var_name not in self.symbol_table:

                self.errors.append(f"Undeclared variable '{var_name}'")

                return False

            # compare types
            return self.symbol_table[var_name] == decl_type

        return False

    # ─────────────────────────────────────────────────────────
    # EXPRESSION
    # ─────────────────────────────────────────────────────────
    def _parse_term(self):

        tok = self._peek()

        if tok and tok[1] in (
            TOKEN_IDENTIFIER,
            TOKEN_NUMBER,
            TOKEN_STRING,
            TOKEN_CHAR,
            TOKEN_BOOL,
        ):

            self._advance()

            leaf = self._leaf(tok[0], tok[1])

            return self._node(
                "Term",
                "structural",
                [leaf],
            )

        return None

    def _parse_expression(self):

        term = self._parse_term()

        if not term:
            return None

        children = [term]

        while (
            self._peek()
            and self._peek()[1] == TOKEN_OPERATOR
            and self._peek()[0] in ("+", "-", "*", "/")
        ):

            op_tok = self._advance()

            op_leaf = self._leaf(
                op_tok[0],
                TOKEN_OPERATOR,
            )

            next_term = self._parse_term()

            if not next_term:
                return None

            children.append(op_leaf)
            children.append(next_term)

        return self._node(
            "Expression",
            "structural",
            children,
        )

    # ─────────────────────────────────────────────────────────
    # DECLARATION
    # ─────────────────────────────────────────────────────────
    def _parse_declaration(self):

        start = self.pos

        kw = self._peek()

        if not (kw and kw[1] == TOKEN_KEYWORD and kw[0] in DECL_TYPES):
            return None

        self._advance()

        ident = self._expect(kind=TOKEN_IDENTIFIER)

        if not ident:

            self.errors.append(f"Expected identifier after '{kw[0]}'")

            self.pos = start

            return None

        eq = self._expect(value="=")

        if not eq:

            self.errors.append(f"Expected '=' in declaration")

            self.pos = start

            return None

        expr = self._parse_expression()

        if not expr:

            self.errors.append(f"Expected expression in declaration")

            self.pos = start

            return None

        # SEMANTIC CHECK
        if not self._is_type_compatible(kw[0], expr):

            self.errors.append(f"Type mismatch for variable '{ident[0]}'")

            self.pos = start

            return None

        # STORE VARIABLE TYPE
        self.symbol_table[ident[0]] = kw[0]

        semi = self._expect(value=";")

        if not semi:

            self.errors.append(f"Missing ';' at end of declaration")

            self.pos = start

            return None

        node = self._node(
            "Declaration",
            "structural",
            [
                self._leaf(kw[0], TOKEN_KEYWORD),
                self._leaf(ident[0], TOKEN_IDENTIFIER),
                self._leaf("=", TOKEN_OPERATOR),
                expr,
                self._leaf(";", TOKEN_SYMBOL),
            ],
        )

        return {
            "type": "Declaration",
            "keyword": kw[0],
            "ident": ident[0],
            "node": node,
        }

    # ─────────────────────────────────────────────────────────
    # ASSIGNMENT
    # ─────────────────────────────────────────────────────────
    def _parse_assignment(self):

        start = self.pos

        ident = self._expect(kind=TOKEN_IDENTIFIER)

        if not ident:
            return None

        # variable must exist
        if ident[0] not in self.symbol_table:

            self.errors.append(f"Undeclared variable '{ident[0]}'")

            self.pos = start

            return None

        eq = self._expect(value="=")

        if not eq:

            self.pos = start

            return None

        expr = self._parse_expression()

        if not expr:

            self.errors.append(f"Expected expression in assignment")

            self.pos = start

            return None

        # semantic assignment check
        var_type = self.symbol_table[ident[0]]

        if not self._is_type_compatible(var_type, expr):

            self.errors.append(f"Type mismatch in assignment to '{ident[0]}'")

            self.pos = start

            return None

        semi = self._expect(value=";")

        if not semi:

            self.errors.append(f"Missing ';' at end of assignment")

            self.pos = start

            return None

        node = self._node(
            "Assignment",
            "structural",
            [
                self._leaf(ident[0], TOKEN_IDENTIFIER),
                self._leaf("=", TOKEN_OPERATOR),
                expr,
                self._leaf(";", TOKEN_SYMBOL),
            ],
        )

        return {
            "type": "Assignment",
            "ident": ident[0],
            "node": node,
        }

    # ─────────────────────────────────────────────────────────
    # MAIN PARSE
    # ─────────────────────────────────────────────────────────
    def parse(self):

        self.results.clear()
        self.errors.clear()

        self.pos = 0
        self._nid = 0

        stmt_nodes = []

        while self.pos < len(self.tokens):

            tok = self._peek()

            if not tok:
                break

            # DECLARATION
            if tok[1] == TOKEN_KEYWORD and tok[0] in DECL_TYPES:

                r = self._parse_declaration()

                if r:
                    self.results.append(r)
                    stmt_nodes.append(r["node"])

                    continue

            # ASSIGNMENT
            r = self._parse_assignment()

            if r:

                self.results.append(r)
                stmt_nodes.append(r["node"])

                continue

            # ERROR RECOVERY
            tok = self._peek()

            if tok:

                self.errors.append(f"Syntax error near '{tok[0]}'")

                while self.pos < len(self.tokens) and self.tokens[self.pos][0] != ";":
                    self.pos += 1

                if self.pos < len(self.tokens):
                    self.pos += 1

        self.tree = self._node(
            "Program",
            "structural",
            stmt_nodes,
        )

        return self.results


# ─────────────────────────────────────────────────────────────
# STREAMLIT UI
# ─────────────────────────────────────────────────────────────
st.title("⬡ Mini Compiler")

source = st.text_area(
    "Enter Source Code",
    value=SAMPLE_CODE,
    height=300,
)

if st.button("▶ Run Analysis"):

    lexer = Lexer(source)

    tokens = lexer.tokenize()

    parser = Parser(tokens)

    results = parser.parse()

    # TOKENS
    st.subheader("🔍 Tokens")

    token_rows = []

    for i, (value, tt, line) in enumerate(tokens):

        token_rows.append(
            {
                "#": i + 1,
                "Value": value,
                "Type": tt,
                "Line": line,
            }
        )

    st.dataframe(
        pd.DataFrame(token_rows),
        width="stretch",
        hide_index=True,
    )

    # REPORT
    st.subheader("✅ Syntax / Semantic Report")

    for r in results:

        if r["type"] == "Declaration":

            st.success(f"✔ Valid Declaration → {r['keyword']} {r['ident']}")

        elif r["type"] == "Assignment":

            st.success(f"✔ Valid Assignment → {r['ident']}")

    # ERRORS
    if lexer.errors:

        st.subheader("❌ Lexical Errors")

        for err in lexer.errors:
            st.error(err)

    if parser.errors:

        st.subheader("❌ Syntax / Semantic Errors")

        for err in parser.errors:
            st.error(err)

    # SYMBOL TABLE
    st.subheader("🧠 Symbol Table")

    if parser.symbol_table:

        symbol_rows = []

        for var, typ in parser.symbol_table.items():

            symbol_rows.append(
                {
                    "Variable": var,
                    "Type": typ,
                }
            )

        st.table(pd.DataFrame(symbol_rows))

    else:
        st.info("No variables declared.")

    # PARSE TREE
    if parser.tree:

        st.subheader("🌳 Parse Tree")

        dot_src = tree_to_dot(parser.tree)

        st.graphviz_chart(
            dot_src,
            width="stretch",
        )

        with st.expander("DOT Source"):

            st.code(dot_src, language="dot")

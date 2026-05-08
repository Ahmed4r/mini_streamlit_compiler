"""
Mini Compiler Front-End  ·  CS 404 — Compiler Design
Pharos University in Alexandria
Lexical Analyzer + Syntax Analyzer + Parse Tree  ·  Streamlit Edition
"""

import re
import streamlit as st
import pandas as pd
from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Mini Compiler · CS 404",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ─────────────────────────────────────────────────────────────
#  TOKEN CONSTANTS
# ─────────────────────────────────────────────────────────────
TOKEN_KEYWORD = "KEYWORD"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_NUMBER = "NUMBER"
TOKEN_OPERATOR = "OPERATOR"
TOKEN_SYMBOL = "SYMBOL"
TOKEN_STRING = "STRING"
TOKEN_BOOL = "BOOL_LIT"
TOKEN_UNKNOWN = "UNKNOWN"

# ── All supported keywords / types ───────────────────────────
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

# Types that may appear in a declaration
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

# Boolean literal values
BOOL_LITERALS = {"true", "false"}

TYPE_ICONS = {
    TOKEN_KEYWORD: "◆",
    TOKEN_IDENTIFIER: "◈",
    TOKEN_NUMBER: "●",
    TOKEN_OPERATOR: "◉",
    TOKEN_SYMBOL: "◇",
    TOKEN_STRING: "❝",
    TOKEN_BOOL: "⬡",
    TOKEN_UNKNOWN: "✕",
}

NODE_COLORS = {
    "structural": ("#1e3a5f", "#93c5fd"),
    "keyword": ("#4a1942", "#f0abfc"),
    "identifier": ("#14402e", "#6ee7b7"),
    "number": ("#3b1f6e", "#c4b5fd"),
    "operator": ("#4d2c06", "#fcd34d"),
    "symbol": ("#1e293b", "#94a3b8"),
    "string": ("#1a3a2a", "#34d399"),
    "bool": ("#3b2a00", "#fbbf24"),
    "error": ("#7f1d1d", "#fca5a5"),
    "default": ("#1e293b", "#e2e8f0"),
}

SAMPLE_CODE = (
    "int x = 5;\n"
    "float y = 3.2;\n"
    "double d = 9.99;\n"
    "char c = 'A';\n"
    "bool flag = true;\n"
    "long big = 123456;\n"
    "short s = 10;\n"
    'string name = "Alice";\n'
    "x = x + 10;\n"
    "y = y + d;"
)


# ─────────────────────────────────────────────────────────────
#  PARSE TREE NODE
# ─────────────────────────────────────────────────────────────
@dataclass
class TreeNode:
    nid: str
    label: str
    category: str = "default"
    children: list = field(default_factory=list)


# ─────────────────────────────────────────────────────────────
#  DOT GENERATOR
# ─────────────────────────────────────────────────────────────
def tree_to_dot(root: TreeNode) -> str:
    lines = [
        "digraph ParseTree {",
        '  graph [rankdir=TB, nodesep=0.5, ranksep=0.7, bgcolor="transparent"];',
        '  node [fontname="Courier New", fontsize=10, shape=box,'
        '        style="rounded,filled", margin="0.15,0.1"];',
        '  edge [color="#475569", arrowsize=0.65, penwidth=1.2];',
    ]

    def walk(node: TreeNode):
        fill, font = NODE_COLORS.get(node.category, NODE_COLORS["default"])
        safe_label = node.label.replace('"', '\\"').replace("\n", "\\n")

        lines.append(
            f'  {node.nid} [label="{safe_label}", '
            f'fillcolor="{fill}", fontcolor="{font}", '
            f'color="{fill}"];'
        )

        for child in node.children:
            lines.append(f"  {node.nid} -> {child.nid};")
            walk(child)

    walk(root)
    lines.append("}")
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
#  LEXICAL ANALYZER
# ─────────────────────────────────────────────────────────────
class Lexer:
    def __init__(self, source: str):
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
            ("CHAR_LIT", r"'[^']{0,1}'"),
            ("FLOAT_NUM", r"\d+\.\d+"),
            ("INT_NUM", r"\d+"),
            # KEYWORDS BEFORE IDENTIFIERS
            ("KEYWORD", self.kw_regex),
            ("IDENT", r"[A-Za-z_][A-Za-z0-9_]*"),
            ("OP", r"==|!=|<=|>=|&&|\|\||[=+\-*/!<>%]"),
            ("SYM", r"[;(){}[\],.]"),
            ("COMMENT", r"//[^\n]*"),
            ("SKIP", r"[ \t]+"),
            ("NEWLINE", r"\n"),
            ("MISMATCH", r"."),
        ]

        pattern = "|".join(f"(?P<{n}>{r})" for n, r in token_spec)

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
                self.tokens.append((value, TOKEN_STRING, line_num))

            elif kind in ("FLOAT_NUM", "INT_NUM"):
                self.tokens.append((value, TOKEN_NUMBER, line_num))

            # FIXED SECTION
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
#  SYNTAX ANALYZER
# ─────────────────────────────────────────────────────────────
class Parser:
    def __init__(self, tokens):
        self.tokens = [(v, t) for v, t, _ in tokens]
        self.pos = 0
        self.results = []
        self.errors = []
        self.tree = None
        self._nid = 0

    # ─────────────────────────────────────────────────────────
    # Helpers
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
            TOKEN_BOOL: "bool",
            TOKEN_UNKNOWN: "error",
        }

        cat = cat_map.get(token_type, "default")

        label = f"{value}\n({token_type})"

        return self._node(label, cat)

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

        if tok is None:
            return None

        v, k = tok

        if (value is None or v == value) and (kind is None or k == kind):
            return self._advance()

        return None

    # ─────────────────────────────────────────────────────────
    # Grammar
    # ─────────────────────────────────────────────────────────
    def _parse_term(self):
        tok = self._peek()

        if tok and tok[1] in (
            TOKEN_IDENTIFIER,
            TOKEN_NUMBER,
            TOKEN_STRING,
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
            and self._peek()[0] in ("+", "-", "*", "/", "%")
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
            self.errors.append(f"Expected '=' in declaration of '{ident[0]}'")
            self.pos = start
            return None

        expr = self._parse_expression()

        if not expr:
            self.errors.append(f"Expected expression in declaration of '{ident[0]}'")
            self.pos = start
            return None

        semi = self._expect(value=";")

        if not semi:
            self.errors.append(f"Missing ';' at end of declaration of '{ident[0]}'")
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

    def _parse_assignment(self):
        start = self.pos

        ident = self._expect(kind=TOKEN_IDENTIFIER)

        if not ident:
            self.pos = start
            return None

        eq = self._expect(value="=")

        if not eq:
            self.pos = start
            return None

        expr = self._parse_expression()

        if not expr:
            self.errors.append(f"Expected expression in assignment to '{ident[0]}'")
            self.pos = start
            return None

        semi = self._expect(value=";")

        if not semi:
            self.errors.append(f"Missing ';' at end of assignment to '{ident[0]}'")
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
    # Main Parse
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
#  STREAMLIT UI
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
        use_container_width=True,
        hide_index=True,
    )

    # RESULTS
    st.subheader("✅ Syntax Report")

    if results:
        for r in results:

            if r["type"] == "Declaration":
                st.success(f"✔ Valid Declaration → {r['keyword']} {r['ident']}")

            elif r["type"] == "Assignment":
                st.success(f"✔ Valid Assignment → {r['ident']}")

    if lexer.errors:
        st.subheader("❌ Lexical Errors")

        for err in lexer.errors:
            st.error(err)

    if parser.errors:
        st.subheader("❌ Syntax Errors")

        for err in parser.errors:
            st.error(err)

    # PARSE TREE
    if parser.tree:
        st.subheader("🌳 Parse Tree")

        dot_src = tree_to_dot(parser.tree)

        st.graphviz_chart(
            dot_src,
            use_container_width=True,
        )

        with st.expander("DOT Source"):
            st.code(dot_src, language="dot")

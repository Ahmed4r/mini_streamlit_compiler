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
TOKEN_KEYWORD    = "KEYWORD"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_NUMBER     = "NUMBER"
TOKEN_OPERATOR   = "OPERATOR"
TOKEN_SYMBOL     = "SYMBOL"
TOKEN_UNKNOWN    = "UNKNOWN"

KEYWORDS = {"int", "float"}

TYPE_ICONS = {
    TOKEN_KEYWORD:    "◆",
    TOKEN_IDENTIFIER: "◈",
    TOKEN_NUMBER:     "●",
    TOKEN_OPERATOR:   "◉",
    TOKEN_SYMBOL:     "◇",
    TOKEN_UNKNOWN:    "✕",
}

# Node fill/font colours used in the DOT graph
NODE_COLORS = {
    "structural": ("#1e3a5f", "#93c5fd"),   # Program / Declaration / Assignment / Expression / Term
    "keyword":    ("#4a1942", "#f0abfc"),
    "identifier": ("#14402e", "#6ee7b7"),
    "number":     ("#3b1f6e", "#c4b5fd"),
    "operator":   ("#4d2c06", "#fcd34d"),
    "symbol":     ("#1e293b", "#94a3b8"),
    "error":      ("#7f1d1d", "#fca5a5"),
    "default":    ("#1e293b", "#e2e8f0"),
}

SAMPLE_CODE = "int x = 5;\nfloat y = 3.2;\nx = x + 10;"

STRUCTURAL_LABELS = {"Program", "Declaration", "Assignment", "Expression", "Term"}


# ─────────────────────────────────────────────────────────────
#  PARSE TREE NODE
# ─────────────────────────────────────────────────────────────
@dataclass
class TreeNode:
    nid:      str
    label:    str
    category: str = "default"          # controls colour in DOT
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
        # Escape special chars and convert newlines for DOT
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
        self.tokens: list[tuple[str, str, int]] = []
        self.errors: list[str] = []

    def tokenize(self) -> list[tuple[str, str, int]]:
        self.tokens.clear()
        self.errors.clear()
        token_spec = [
            ("FLOAT_NUM", r"\d+\.\d+"),
            ("INT_NUM",   r"\d+"),
            ("IDENT",     r"[A-Za-z_][A-Za-z0-9_]*"),
            ("OP",        r"[=+\-*/]"),
            ("SYM",       r"[;(){}]"),
            ("SKIP",      r"[ \t]+"),
            ("NEWLINE",   r"\n"),
            ("MISMATCH",  r"."),
        ]
        pattern = "|".join(f"(?P<{n}>{r})" for n, r in token_spec)
        line_num = 1

        for mo in re.finditer(pattern, self.source):
            kind  = mo.lastgroup
            value = mo.group()
            if kind in ("SKIP", "NEWLINE"):
                if kind == "NEWLINE":
                    line_num += 1
                continue
            elif kind == "MISMATCH":
                self.errors.append(f"Line {line_num}: Unexpected character '{value}'")
                self.tokens.append((value, TOKEN_UNKNOWN, line_num))
            elif kind in ("FLOAT_NUM", "INT_NUM"):
                self.tokens.append((value, TOKEN_NUMBER, line_num))
            elif kind == "IDENT":
                tt = TOKEN_KEYWORD if value in KEYWORDS else TOKEN_IDENTIFIER
                self.tokens.append((value, tt, line_num))
            elif kind == "OP":
                self.tokens.append((value, TOKEN_OPERATOR, line_num))
            elif kind == "SYM":
                self.tokens.append((value, TOKEN_SYMBOL, line_num))

        return self.tokens


# ─────────────────────────────────────────────────────────────
#  SYNTAX ANALYZER  (now also builds a parse tree)
# ─────────────────────────────────────────────────────────────
class Parser:
    def __init__(self, tokens: list[tuple[str, str, int]]):
        self.tokens  = [(v, t) for v, t, _ in tokens]
        self.pos     = 0
        self.results: list[dict] = []
        self.errors:  list[str]  = []
        self.tree:    Optional[TreeNode] = None
        self._nid    = 0

    # ── helpers ───────────────────────────────────────────────
    def _node(self, label: str, category: str = "default",
              children: list | None = None) -> TreeNode:
        self._nid += 1
        return TreeNode(f"n{self._nid}", label, category, children or [])

    def _leaf(self, value: str, token_type: str) -> TreeNode:
        cat_map = {
            TOKEN_KEYWORD:    "keyword",
            TOKEN_IDENTIFIER: "identifier",
            TOKEN_NUMBER:     "number",
            TOKEN_OPERATOR:   "operator",
            TOKEN_SYMBOL:     "symbol",
            TOKEN_UNKNOWN:    "error",
        }
        cat   = cat_map.get(token_type, "default")
        label = f"{value}\n({token_type})"
        return self._node(label, cat)

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        tok = self.tokens[self.pos]; self.pos += 1; return tok

    def _expect(self, value=None, kind=None):
        tok = self._peek()
        if tok is None:
            return None
        v, k = tok
        if (value is None or v == value) and (kind is None or k == kind):
            return self._advance()
        return None

    # ── grammar productions (return TreeNode or None) ─────────
    def _parse_term(self) -> Optional[TreeNode]:
        """term → IDENTIFIER | NUMBER"""
        tok = self._peek()
        if tok and tok[1] in (TOKEN_IDENTIFIER, TOKEN_NUMBER):
            self._advance()
            leaf = self._leaf(tok[0], tok[1])
            return self._node("Term", "structural", [leaf])
        return None

    def _parse_expression(self) -> Optional[TreeNode]:
        """expression → term ( '+' term )*"""
        term = self._parse_term()
        if not term:
            return None
        children: list[TreeNode] = [term]
        while self._peek() and self._peek()[0] == "+":
            op_tok = self._advance()
            op_leaf = self._leaf(op_tok[0], TOKEN_OPERATOR)
            next_term = self._parse_term()
            if not next_term:
                return None
            children.append(op_leaf)
            children.append(next_term)
        return self._node("Expression", "structural", children)

    def _parse_declaration(self) -> Optional[dict]:
        """declaration → KEYWORD IDENTIFIER '=' expression ';'"""
        start = self.pos
        kw = self._expect(kind=TOKEN_KEYWORD)
        if not kw:
            self.pos = start; return None
        ident = self._expect(kind=TOKEN_IDENTIFIER)
        if not ident:
            self.pos = start; return None
        eq = self._expect(value="=")
        if not eq:
            self.pos = start; return None
        expr = self._parse_expression()
        if not expr:
            self.pos = start; return None
        semi = self._expect(value=";")
        if not semi:
            self.pos = start; return None

        node = self._node("Declaration", "structural", [
            self._leaf(kw[0],    TOKEN_KEYWORD),
            self._leaf(ident[0], TOKEN_IDENTIFIER),
            self._leaf("=",      TOKEN_OPERATOR),
            expr,
            self._leaf(";",      TOKEN_SYMBOL),
        ])
        return {"type": "Declaration", "keyword": kw[0], "ident": ident[0], "node": node}

    def _parse_assignment(self) -> Optional[dict]:
        """assignment → IDENTIFIER '=' expression ';'"""
        start = self.pos
        ident = self._expect(kind=TOKEN_IDENTIFIER)
        if not ident:
            self.pos = start; return None
        eq = self._expect(value="=")
        if not eq:
            self.pos = start; return None
        expr = self._parse_expression()
        if not expr:
            self.pos = start; return None
        semi = self._expect(value=";")
        if not semi:
            self.pos = start; return None

        node = self._node("Assignment", "structural", [
            self._leaf(ident[0], TOKEN_IDENTIFIER),
            self._leaf("=",      TOKEN_OPERATOR),
            expr,
            self._leaf(";",      TOKEN_SYMBOL),
        ])
        return {"type": "Assignment", "ident": ident[0], "node": node}

    # ── top-level parse ───────────────────────────────────────
    def parse(self) -> list[dict]:
        self.results.clear()
        self.errors.clear()
        self.pos  = 0
        self._nid = 0

        stmt_nodes: list[TreeNode] = []

        while self.pos < len(self.tokens):
            r = self._parse_declaration()
            if r:
                self.results.append(r)
                stmt_nodes.append(r["node"])
                continue
            r = self._parse_assignment()
            if r:
                self.results.append(r)
                stmt_nodes.append(r["node"])
                continue
            tok = self._peek()
            if tok:
                self.errors.append(f"Syntax error near '{tok[0]}'")
                # error-recovery: skip to next semicolon
                while self.pos < len(self.tokens) and self.tokens[self.pos][0] != ";":
                    self.pos += 1
                if self.pos < len(self.tokens):
                    self.pos += 1

        self.tree = self._node("Program", "structural", stmt_nodes)
        return self.results


# ─────────────────────────────────────────────────────────────
#  SESSION STATE
# ─────────────────────────────────────────────────────────────
defaults: dict = {
    "tokens":         [],
    "results":        [],
    "syn_errors":     [],
    "lex_errors":     [],
    "analyzed":       False,
    "editor_content": SAMPLE_CODE,
    "parse_tree_dot": "",
}
for key, val in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = val


# ─────────────────────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────────────────────
st.title("⬡  Mini Compiler")
st.caption(
    "CS 404 · Compiler Design · Pharos University in Alexandria  |  "
    "Dr. Alaa Radwan · Eng. Mayar Mohamed"
)
st.divider()


# ─────────────────────────────────────────────────────────────
#  LAYOUT
# ─────────────────────────────────────────────────────────────
left, right = st.columns([1, 1.4], gap="large")


# ── LEFT — SOURCE CODE ───────────────────────────────────────
with left:
    st.subheader("📝  Source Code")

    source = st.text_area(
        label="Write your mini-language code here:",
        value=st.session_state.editor_content,
        height=220,
    )

    with st.expander("Token Types Legend"):
        c1, c2, c3 = st.columns(3)
        c1.markdown("◆ `KEYWORD`\n\n◈ `IDENTIFIER`")
        c2.markdown("● `NUMBER`\n\n◉ `OPERATOR`")
        c3.markdown("◇ `SYMBOL`\n\n✕ `UNKNOWN`")

    b1, b2, b3 = st.columns(3)
    with b1:
        run = st.button("▶  Run Analysis", type="primary", use_container_width=True)
    with b2:
        sample_btn = st.button("⊞  Load Sample", use_container_width=True)
    with b3:
        clear_btn = st.button("✕  Clear", use_container_width=True)

    # ── Button actions ──
    if sample_btn:
        st.session_state.editor_content = SAMPLE_CODE
        st.rerun()

    if clear_btn:
        st.session_state.editor_content = ""
        st.session_state.analyzed       = False
        st.session_state.tokens         = []
        st.session_state.results        = []
        st.session_state.syn_errors     = []
        st.session_state.lex_errors     = []
        st.session_state.parse_tree_dot = ""
        st.rerun()

    if run:
        if not source.strip():
            st.warning("Please enter some source code first.")
        else:
            st.session_state.editor_content = source

            lexer   = Lexer(source)
            tokens  = lexer.tokenize()
            parser  = Parser(tokens)
            results = parser.parse()

            st.session_state.tokens         = tokens
            st.session_state.results        = results
            st.session_state.syn_errors     = parser.errors
            st.session_state.lex_errors     = lexer.errors
            st.session_state.analyzed       = True
            st.session_state.parse_tree_dot = (
                tree_to_dot(parser.tree) if parser.tree else ""
            )
            st.rerun()

    # ── Metrics ──
    if st.session_state.analyzed:
        st.divider()
        total_errors = len(st.session_state.syn_errors) + len(st.session_state.lex_errors)

        m1, m2, m3 = st.columns(3)
        m1.metric("Tokens",     len(st.session_state.tokens))
        m2.metric("Statements", len(st.session_state.results))
        m3.metric("Errors",     total_errors)

        if total_errors == 0:
            st.success("✔  All checks passed — syntax is valid")
        else:
            st.error(f"✕  {total_errors} error(s) found — syntax is invalid")

        # ── Grammar reference ──
        with st.expander("📖  Grammar Reference"):
            st.code(
                "program    → statement*\n"
                "statement  → declaration | assignment\n"
                "declaration→ KEYWORD IDENTIFIER '=' expression ';'\n"
                "assignment → IDENTIFIER '=' expression ';'\n"
                "expression → term ( '+' term )*\n"
                "term       → IDENTIFIER | NUMBER",
                language="text",
            )


# ── RIGHT — OUTPUT (tabbed) ──────────────────────────────────
with right:
    if not st.session_state.analyzed:
        st.info("Run the analysis to see results here.")
    else:
        tokens     = st.session_state.tokens
        results    = st.session_state.results
        syn_errors = st.session_state.syn_errors
        lex_errors = st.session_state.lex_errors
        dot_src    = st.session_state.parse_tree_dot

        tab_tokens, tab_syntax, tab_tree = st.tabs(
            ["🔍 Token Stream", "✅ Syntax Report", "🌳 Parse Tree"]
        )

        # ── Tab 1: Token Stream ──────────────────────────────
        with tab_tokens:
            rows = [
                {
                    "#":     i + 1,
                    "Value": value,
                    "Type":  f"{TYPE_ICONS.get(tt, '·')}  {tt}",
                    "Line":  line,
                }
                for i, (value, tt, line) in enumerate(tokens)
            ]

            st.dataframe(
                pd.DataFrame(rows),
                use_container_width=True,
                hide_index=True,
                height=min(36 * len(rows) + 38, 420),
                column_config={
                    "#":     st.column_config.NumberColumn(width="small"),
                    "Value": st.column_config.TextColumn(width="small"),
                    "Type":  st.column_config.TextColumn(width="medium"),
                    "Line":  st.column_config.NumberColumn(width="small"),
                },
            )

            with st.expander("Token Type Breakdown"):
                tok_counts: dict[str, int] = {}
                for _, tt, _ in tokens:
                    tok_counts[tt] = tok_counts.get(tt, 0) + 1
                cols = st.columns(len(tok_counts))
                for col, (tt, cnt) in zip(cols, tok_counts.items()):
                    col.metric(label=f"{TYPE_ICONS.get(tt, '·')} {tt}", value=cnt)

        # ── Tab 2: Syntax Report ─────────────────────────────
        with tab_syntax:
            if results:
                for r in results:
                    if r["type"] == "Declaration":
                        st.success(f"✔  Valid Declaration  →  `{r['keyword']} {r['ident']}`")
                    elif r["type"] == "Assignment":
                        st.success(f"✔  Valid Assignment   →  `{r['ident']}`")
            else:
                st.warning("No parseable statements found.")

            if lex_errors:
                st.divider()
                st.markdown("**Lexical Errors**")
                for err in lex_errors:
                    st.error(f"✕  {err}")

            if syn_errors:
                st.divider()
                st.markdown("**Syntax Errors**")
                for err in syn_errors:
                    st.error(f"✕  {err}")

        # ── Tab 3: Parse Tree ────────────────────────────────
        with tab_tree:
            if dot_src:
                # colour legend
                leg_cols = st.columns(6)
                legend_items = [
                    ("🟦", "Structural"),
                    ("🟣", "Keyword"),
                    ("🟢", "Identifier"),
                    ("🟪", "Number"),
                    ("🟡", "Operator"),
                    ("⬛", "Symbol"),
                ]
                for col, (icon, label) in zip(leg_cols, legend_items):
                    col.markdown(f"{icon} `{label}`")

                st.divider()
                st.graphviz_chart(dot_src, use_container_width=True)

                with st.expander("🔢  Raw DOT Source"):
                    st.code(dot_src, language="dot")
            else:
                st.warning("No parse tree available — check for syntax errors.")
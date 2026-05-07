"""
Mini Compiler Front-End  ·  CS 404 — Compiler Design
Pharos University in Alexandria
Lexical Analyzer + Syntax Analyzer  ·  Streamlit Edition
"""

import re
import streamlit as st
import pandas as pd

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

SAMPLE_CODE = "int x = 5;\nfloat y = 3.2;\nx = x + 10;"


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
#  SYNTAX ANALYZER
# ─────────────────────────────────────────────────────────────
class Parser:
    def __init__(self, tokens: list[tuple[str, str, int]]):
        self.tokens  = [(v, t) for v, t, _ in tokens]
        self.pos     = 0
        self.results: list[dict] = []
        self.errors:  list[str]  = []

    def _peek(self):
        return self.tokens[self.pos] if self.pos < len(self.tokens) else None

    def _advance(self):
        tok = self.tokens[self.pos]; self.pos += 1; return tok

    def _expect(self, value=None, kind=None):
        tok = self._peek()
        if tok is None: return None
        v, k = tok
        if (value is None or v == value) and (kind is None or k == kind):
            return self._advance()
        return None

    def _parse_term(self) -> bool:
        tok = self._peek()
        if tok and tok[1] in (TOKEN_IDENTIFIER, TOKEN_NUMBER):
            self._advance(); return True
        return False

    def _parse_expression(self) -> bool:
        if not self._parse_term(): return False
        while self._peek() and self._peek()[0] == "+":
            self._advance()
            if not self._parse_term(): return False
        return True

    def _parse_declaration(self):
        start = self.pos
        kw    = self._expect(kind=TOKEN_KEYWORD)
        if not kw: self.pos = start; return None
        ident = self._expect(kind=TOKEN_IDENTIFIER)
        if not ident: self.pos = start; return None
        if not self._expect(value="="): self.pos = start; return None
        if not self._parse_expression(): self.pos = start; return None
        if not self._expect(value=";"): self.pos = start; return None
        return {"type": "Declaration", "keyword": kw[0], "ident": ident[0]}

    def _parse_assignment(self):
        start = self.pos
        ident = self._expect(kind=TOKEN_IDENTIFIER)
        if not ident: self.pos = start; return None
        if not self._expect(value="="): self.pos = start; return None
        if not self._parse_expression(): self.pos = start; return None
        if not self._expect(value=";"): self.pos = start; return None
        return {"type": "Assignment", "ident": ident[0]}

    def parse(self) -> list[dict]:
        self.results.clear(); self.errors.clear(); self.pos = 0
        while self.pos < len(self.tokens):
            r = self._parse_declaration()
            if r: self.results.append(r); continue
            r = self._parse_assignment()
            if r: self.results.append(r); continue
            tok = self._peek()
            if tok:
                self.errors.append(f"Syntax error near '{tok[0]}'")
                while self.pos < len(self.tokens) and self.tokens[self.pos][0] != ";":
                    self.pos += 1
                if self.pos < len(self.tokens):
                    self.pos += 1
        return self.results


# ─────────────────────────────────────────────────────────────
#  SESSION STATE  (initialise before any widget)
# ─────────────────────────────────────────────────────────────
defaults = {
    "tokens":         [],
    "results":        [],
    "syn_errors":     [],
    "lex_errors":     [],
    "analyzed":       False,
    "editor_content": SAMPLE_CODE,   # ← separate from widget key
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


# ── LEFT — SOURCE CODE ──────────────────────────────────────
with left:
    st.subheader("📝  Source Code")

    # The widget uses `value` from our own state variable — no `key` needed
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

    # ── Button actions — update editor_content THEN rerun ──
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
        st.rerun()

    if run:
        if not source.strip():
            st.warning("Please enter some source code first.")
        else:
            # Save current editor text so it survives the rerun
            st.session_state.editor_content = source

            lexer   = Lexer(source)
            tokens  = lexer.tokenize()
            parser  = Parser(tokens)
            results = parser.parse()

            st.session_state.tokens     = tokens
            st.session_state.results    = results
            st.session_state.syn_errors = parser.errors
            st.session_state.lex_errors = lexer.errors
            st.session_state.analyzed   = True
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


# ── RIGHT — OUTPUT ────────────────────────────────────────────
with right:
    if not st.session_state.analyzed:
        st.info("Run the analysis to see results here.")
    else:
        tokens     = st.session_state.tokens
        results    = st.session_state.results
        syn_errors = st.session_state.syn_errors
        lex_errors = st.session_state.lex_errors

        # ── Token Stream ──
        st.subheader("🔍  Token Stream")

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
            height=min(36 * len(rows) + 38, 400),
            column_config={
                "#":     st.column_config.NumberColumn(width="small"),
                "Value": st.column_config.TextColumn(width="small"),
                "Type":  st.column_config.TextColumn(width="medium"),
                "Line":  st.column_config.NumberColumn(width="small"),
            },
        )

        # Token type breakdown
        with st.expander("Token Type Breakdown"):
            tok_counts: dict[str, int] = {}
            for _, tt, _ in tokens:
                tok_counts[tt] = tok_counts.get(tt, 0) + 1

            cols = st.columns(len(tok_counts))
            for col, (tt, cnt) in zip(cols, tok_counts.items()):
                col.metric(label=f"{TYPE_ICONS.get(tt, '·')} {tt}", value=cnt)

        st.divider()

        # ── Syntax Report ──
        st.subheader("✅  Syntax Analysis Report")

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
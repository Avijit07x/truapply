from truapply.tracker.plain import readable_changes


def test_skill_line_keeps_text_and_drops_layout() -> None:
    line = r"-\B{Frontend:} React.js, Next.js, Tailwind CSS\par\vspace{1.9pt}"
    assert readable_changes([line]) == ["-Frontend: React.js, Next.js, Tailwind CSS"]


def test_item_becomes_bullet() -> None:
    line = r"+\item Grew it into a \B{pnpm monorepo} with Vue 3/Nuxt packages, plus a CLI"
    assert readable_changes([line]) == [
        "+• Grew it into a pnpm monorepo with Vue 3/Nuxt packages, plus a CLI"
    ]


def test_custom_command_arguments_are_joined() -> None:
    line = (
        r"-\project{acme-ui}{\href{https://acme.dev}{acme.dev}\sep "
        r"\href{https://github.com/x/acme-ui}{github.com/x/acme-ui}}{May 2026 -- Present}"
    )
    assert readable_changes([line]) == [
        "-acme-ui · acme.dev · github.com/x/acme-ui · May 2026 \u2013 Present"
    ]


def test_font_commands_keep_their_text() -> None:
    line = r"+Built \textbf{fast} and \emph{tidy} pages, \textit{quietly}"
    assert readable_changes([line]) == ["+Built fast and tidy pages, quietly"]


def test_escaped_symbols_and_ties() -> None:
    line = r"+Cut load by 30\% for R\&D at \$5 cost, ticket \#12, page~2"
    assert readable_changes([line]) == ["+Cut load by 30% for R&D at $5 cost, ticket #12, page 2"]


def test_pure_layout_lines_are_dropped() -> None:
    lines = [r"-\vspace{4pt}", r"+\par\hfill", r"-\end{itemize}", r"+\\[2pt]", "+", "-  "]
    assert readable_changes(lines) == []


def test_plain_lines_stay_unchanged() -> None:
    lines = ["-Built 40 components -- fast~ish", "+Built 40 shared React components."]
    assert readable_changes(lines) == lines


def test_nested_braces_are_unwrapped() -> None:
    line = r"+\role{Engineer {\bfseries II}}{Example Co -- Remote}{2024}"
    assert readable_changes([line]) == ["+Engineer II · Example Co \u2013 Remote · 2024"]


def test_whitespace_collapses_and_line_break_spaces_words() -> None:
    line = r"-Line one\\ line   two\hspace{3mm}end"
    assert readable_changes([line]) == ["-Line one line two end"]


def test_broken_latex_never_raises() -> None:
    lines = [r"+\B{unclosed \href{x", "-\\", r"+trailing \sep", "+" + "{" * 2000 + r"\B{x}"]
    assert readable_changes(lines) == ["+unclosed x", "+trailing", "+" + "{" * 2000 + r"\B{x}"]


def test_comments_are_removed() -> None:
    assert readable_changes([r"+\B{Kept} text % note to self"]) == ["+Kept text"]


def test_whole_line_comments_are_dropped() -> None:
    assert readable_changes(["-% ==== Projects ====", "+  % spacing tweak"]) == []

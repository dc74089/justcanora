"""Rendering chat messages to HTML.

Two audiences, two rules. Agent messages are Markdown and are rendered as such,
with raw HTML escaped rather than trusted. Student messages are *not* Markdown —
they are whatever a 13-year-old typed or pasted — so nothing is interpreted and
nothing is ever discarded; the text is escaped, whitespace is preserved, and code
is detected only to decide whether to draw a box around it.

That last point matters: this used to strip unrecognised HTML with
BeautifulSoup's get_text(), so a Web Dev student pasting "<h1>My Page</h1>" saw
their markup silently vanish from the transcript. Guessing wrong about code is
now only ever cosmetic.
"""

import re

import markdown2
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from pygments.util import ClassNotFound

register = template.Library()

# markdown2's code-color extra wraps its output in .codehilite; student code is
# highlighted with the same class so one stylesheet covers both.
CODE_CSS_CLASS = "codehilite"

# NB: no "highlightjs-lang" — it overrides code-color and emits a bare
# <code class="language-x"> for a highlight.js that this project never loads,
# which is why nothing was ever highlighted.
AGENT_EXTRAS = [
    "fenced-code-blocks",
    "code-color",        # server-side Pygments; survives the AJAX swaps
    "break-on-newline",  # chat-style single line breaks should be line breaks
    "tables",
]

# The course an agent teaches is the best guess for unlabelled student code.
LANGUAGE_LEXERS = {"python": "python", "java": "java", "html": "html"}

FENCE = re.compile(
    r"^[ \t]*```[ \t]*([\w+#.-]*)[ \t]*\n(.*?)^[ \t]*```[ \t]*$",
    re.DOTALL | re.MULTILINE,
)

# Signals that a single line is code. Deliberately conservative about prose:
# "Note: this is tricky" must not read as a CSS declaration.
CODE_LINE = re.compile(
    r"""
      ^[ ]{2,}\S                                   # indented
    | ^\t\S
    | ^\s*</?[A-Za-z][\w-]*[\s/>]                   # an HTML tag
    | [{};]\s*$                                     # Java/CSS statement end
    | ^\s*[a-z-]+\s*:\s*\S.*;\s*$                   # CSS declaration
    | ^\s*(def|class|function|import|from|public|private|protected|static
          |void|return|print|console\.log|System\.out|var|let|const)\b
    | ^\s*(if|elif|else|for|while|try|except|finally|switch)\b.*:\s*$
    | ^\s*[A-Za-z_]\w*\s*=\s*\S                     # assignment
    | ^\s*[\w.]+\([^)]*\)\s*;?\s*$                  # a bare call, e.g. greet("Ada")
    """,
    re.VERBOSE,
)

# Above this share of code-ish lines, treat the whole paste as one block rather
# than slicing it into alternating boxes and paragraphs.
MOSTLY_CODE = 0.6


def lexer_for(name, code):
    """Pygments lexer from an explicit name, else the course language, else a guess."""
    if name:
        try:
            return get_lexer_by_name(LANGUAGE_LEXERS.get(name, name))
        except ClassNotFound:
            pass
    try:
        return guess_lexer(code)
    except ClassNotFound:
        return get_lexer_by_name("text")


def render_code(code, language=None):
    formatter = HtmlFormatter(cssclass=CODE_CSS_CLASS)
    return highlight(code.rstrip("\n"), lexer_for(language, code), formatter)


def render_text(text):
    """Escaped, with whitespace preserved by the .chat-text CSS."""
    return f'<p class="chat-text">{escape(text.strip())}</p>'


def is_code_line(line):
    return bool(line.strip()) and bool(CODE_LINE.search(line))


def split_runs(text):
    """Group lines into consecutive ("code"|"text", lines) runs.

    Runs are built from *consecutive lines*, not blank-line-separated blocks —
    a blank line between two functions is part of the code, and splitting there
    is what used to render half a pasted function as a paragraph.
    """
    lines = text.split("\n")
    flags = [is_code_line(line) for line in lines]

    # A blank line surrounded by code stays with the code.
    for i, line in enumerate(lines):
        if line.strip():
            continue
        before = any(flags[:i][::-1][:1])
        after = any(flags[i + 1:][:1])
        flags[i] = before and after

    runs, start = [], 0
    for i in range(1, len(lines) + 1):
        if i == len(lines) or flags[i] != flags[start]:
            runs.append(("code" if flags[start] else "text", lines[start:i]))
            start = i
    return runs


def is_boxed(kind, lines, only_run):
    """Whether a run earns a code box.

    A lone code-ish line inside prose ("x = 5 is what I tried") shouldn't become
    a box mid-paragraph, so a run needs two lines — unless it's the whole message.
    """
    if kind != "code":
        return False
    return only_run or len([line for line in lines if line.strip()]) >= 2


@register.filter(name="markdown")
def markdown_format(text):
    """Agent messages: real Markdown, with raw HTML escaped rather than trusted."""
    text = (text or "").strip()
    if not text:
        return mark_safe("")  # markdown2 would emit an empty <p> here
    return mark_safe(markdown2.markdown(text, extras=AGENT_EXTRAS, safe_mode="escape"))


@register.filter(name="auto_code_highlight")
def auto_code_highlight(text, language=None):
    """Student messages: never interpreted, never discarded."""
    text = (text or "").strip()
    if not text:
        return mark_safe("")

    out, cursor = [], 0
    for fence in FENCE.finditer(text):
        before = text[cursor:fence.start()]
        if before.strip():
            out.extend(render_plain(before, language))
        out.append(render_code(fence.group(2), fence.group(1) or language))
        cursor = fence.end()

    remainder = text[cursor:]
    if remainder.strip():
        out.extend(render_plain(remainder, language))

    return mark_safe("\n".join(out))


def render_plain(text, language):
    """Render an unfenced stretch, boxing the parts that look like code."""
    body = text.strip("\n")

    # A paste that is mostly code is one paste, even if a line or two (a bare
    # call, a stray comment) doesn't match any signal on its own.
    filled = [line for line in body.split("\n") if line.strip()]
    if filled and sum(is_code_line(line) for line in filled) / len(filled) >= MOSTLY_CODE:
        return [render_code(body, language)]

    runs = split_runs(body)
    rendered = []
    for kind, lines in runs:
        chunk = "\n".join(lines)
        if not chunk.strip():
            continue
        if is_boxed(kind, lines, only_run=len(runs) == 1):
            rendered.append(render_code(chunk, language))
        else:
            rendered.append(render_text(chunk))
    return rendered

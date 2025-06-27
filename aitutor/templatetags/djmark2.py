import markdown2
from bs4 import BeautifulSoup
from django import template
from django.utils.safestring import mark_safe
from pygments.lexers.special import TextLexer

register = template.Library()

@register.filter(name='markdown')
def markdown_format(text):
    extras = ["fenced-code-blocks", "code-color", "highlightjs-lang"]
    html = markdown2.markdown(text, extras=extras)
    return mark_safe(html)


@register.filter(name='auto_code_highlight')
def auto_code_highlight(text):
    """
    Detects code-like blocks in user input and renders them with markdown2 (for syntax highlighting).
    Non-code blocks are wrapped in <p> but NOT markdown-processed.
    """
    blocks = text.strip().split('\n\n')  # basic paragraph/code block split
    rendered_blocks = []

    for block in blocks:
        cleaned = block.strip()

        if not cleaned:
            continue

        # Heuristic: looks like code if it has braces, indentation, semicolons, etc.
        looks_like_code = (
            cleaned.startswith('    ') or
            cleaned.startswith('\t') or
            any(sym in cleaned for sym in ['{', '}', 'void ', 'class ', 'System.out', 'if (', 'while (', 'for (', ':\n  '])
        )

        if looks_like_code:
            # Wrap in fenced block and markdown it
            fenced = f"```\n{cleaned}\n```"
            html = markdown2.markdown(fenced, extras=["fenced-code-blocks", "code-friendly", "highlightjs-lang"])
            rendered_blocks.append(html)
        else:
            # Wrap plain text safely in <p> tags
            safe = BeautifulSoup(cleaned, "html.parser").get_text()
            rendered_blocks.append(f"<p>{safe}</p>")

    return mark_safe('\n'.join(rendered_blocks))
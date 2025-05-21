from django import template
from django.utils.safestring import mark_safe
import markdown2

register = template.Library()

@register.filter(name='markdown')
def markdown_format(text):
    extras = ["fenced-code-blocks", "code-color", "highlightjs-lang"]
    html = markdown2.markdown(text, extras=extras)
    return mark_safe(html)
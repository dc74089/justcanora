from django import template

register = template.Library()


@register.filter
def format_filename(value: str):
    value = value.lower()

    value = value.removesuffix(".md")
    value = value.replace("-", ": ", 1)
    value = value.replace("-", " ")

    value = value.replace("lec", "📖")
    value = value.replace("task", "🧑‍💻")

    value = value.title()

    return value


"""Assembling prompt files from templates.

Prompts are built by splicing one file into another. The old marker was
``-----``, which is also a Markdown horizontal rule — so a persona file or a
teacher-written assessment prompt containing one would splice in the wrong
place, or (since ``str.replace`` hits every occurrence) splice the same block in
twice. The markers are now distinctive, and ``splice`` refuses to guess when a
template doesn't contain exactly one.
"""

BASE_MARKER = "%%BASE%%"
PROMPT_MARKER = "%%PROMPT%%"
COMMON_MARKER = "%%COMMON%%"
DESCRIPTION_START = "%%DESCRIPTION%%"
DESCRIPTION_END = "%%END_DESCRIPTION%%"


class PromptTemplateError(Exception):
    """A prompt template is missing its marker, or has more than one."""


def extract_description(template, source="template"):
    """Split a persona file into its picker description and its prompt text.

    The description is what students read on the agent card, not an instruction
    to the model, so it is removed from what becomes the dev message. Required
    rather than optional: an agent with no description renders as a blank card,
    which is exactly the silent failure this is meant to prevent.

    Returns ``(description, remaining_template)``.
    """
    opens, closes = template.count(DESCRIPTION_START), template.count(DESCRIPTION_END)
    if opens != 1 or closes != 1:
        raise PromptTemplateError(
            f"{source}: expected exactly one {DESCRIPTION_START} ... {DESCRIPTION_END} block, "
            f"found {opens} opening and {closes} closing marker(s)."
        )
    if template.index(DESCRIPTION_END) < template.index(DESCRIPTION_START):
        raise PromptTemplateError(
            f"{source}: {DESCRIPTION_END} appears before {DESCRIPTION_START}."
        )

    head, rest = template.split(DESCRIPTION_START, 1)
    body, tail = rest.split(DESCRIPTION_END, 1)

    description = " ".join(body.split())
    if not description:
        raise PromptTemplateError(f"{source}: the {DESCRIPTION_START} block is empty.")

    return description, f"{head.strip()}\n{tail.strip()}\n".lstrip()


def splice(template, marker, value, source="template"):
    """Replace the single occurrence of ``marker`` in ``template`` with ``value``.

    Raises rather than silently producing a malformed prompt: a duplicated
    marker would repeat a whole rulebook, and a missing one would drop it.
    """
    found = template.count(marker)
    if found != 1:
        raise PromptTemplateError(
            f"{source}: expected exactly one {marker}, found {found}."
        )
    return template.replace(marker, value)

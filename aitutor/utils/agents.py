from PIL import Image
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify

from aitutor.models import Agent
from aitutor.utils.prompts import BASE_MARKER, COMMON_MARKER, extract_description, splice

# Course type -> the language base that carries its course-specific content.
LANGUAGE_BASES = {
    "java": "base-java.txt",
    "python": "base-python.txt",
    "html": "base-html.txt",
}

# Drop "<Agent Name>.png" beside "<Agent Name>.txt" and it becomes the card image.
# Limited to formats browsers actually render — Pillow will happily decode TIFF or
# EPS, which would store fine and then show as a broken image on the picker.
# Deliberately excludes SVG: it can carry script, and these are served from our
# own domain. Matching is case-insensitive, since ".JPG" is what phones produce.
PHOTO_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif")


class AgentImageError(Exception):
    """An agent's image is unreadable, ambiguous, or not really an image."""


def verify_image(path):
    """Confirm the file decodes, so a broken card is caught at import.

    Without this, anything at all — a renamed text file, a truncated download —
    gets copied into media and only shows up as a broken image to students.
    """
    try:
        with Image.open(path) as image:
            detected = image.format
            image.verify()
    except Exception as exc:
        raise AgentImageError(f"{path.name} is not a readable image ({exc}).") from exc
    return detected


def build_language_bases(dir):
    """Assemble each language base by splicing in the shared rules.

    The rules that apply to every tutor — refusal, holding the line, the abuse
    protocol, the output contract — live once in base-common.txt. The language
    files hold only what actually differs, so the three can no longer drift
    apart the way they had.
    """
    common = (dir / "base-common.txt").read_text()

    return {
        language: splice((dir / filename).read_text(), COMMON_MARKER, common, source=filename)
        for language, filename in LANGUAGE_BASES.items()
    }


def find_photo(dir, name):
    """The image sitting next to a persona file, if the teacher dropped one in.

    Case-insensitive on the extension. Refuses to choose when there are several
    candidates — silently preferring one would leave the teacher swapping a file
    and wondering why the card never changed.
    """
    matches = sorted(
        path for path in dir.iterdir()
        if path.is_file() and path.stem == name and path.suffix.lower() in PHOTO_EXTENSIONS
    )

    if not matches:
        return None
    if len(matches) > 1:
        raise AgentImageError(
            f"{name}: found more than one image ({', '.join(p.name for p in matches)}). "
            f"Keep only the one you want."
        )
    return matches[0]


def sync_photo(agent, path):
    """Copy an image from the agents folder into media storage.

    Returns True only when the stored image actually changed. Import runs
    repeatedly, so this compares bytes first — re-saving unconditionally would
    pile up a new suffixed copy in media/agent_photos on every single run.
    """
    verify_image(path)
    data = path.read_bytes()

    if agent.photo:
        try:
            with agent.photo.open("rb") as stored:
                if stored.read() == data:
                    return False
        except (OSError, ValueError):
            pass  # row points at a file that's gone; fall through and re-save
        agent.photo.delete(save=False)

    agent.photo.save(
        f"{slugify(agent.name)}-{agent.language}{path.suffix.lower()}",
        ContentFile(data),
        save=True,
    )
    return True


def construct_agents():
    """Rebuild every agent from the files in aitutor/agents.

    Prompt text, card description, and card image are all file-driven, so the
    folder is the source of truth and an import is repeatable. Agents whose file
    has been removed are left alone — retiring one is a deliberate act, not
    something a re-import should do silently.
    """
    dir = settings.BASE_DIR / "aitutor/agents"
    bases = build_language_bases(dir)
    summary = {"agents": 0, "photos": 0, "without_photo": [],
               "image_errors": [], "unmatched_images": []}
    names = set()

    for file in sorted(dir.glob("*.txt")):
        if not file.is_file() or file.name.startswith("base-"):
            continue

        name = file.name.removesuffix(".txt")
        names.add(name)
        description, flavor = extract_description(file.read_text(), source=file.name)

        # A bad image must not stop the prompts from updating — those are the
        # reason to run this, and a deploy shouldn't fail over a card picture.
        try:
            photo = find_photo(dir, name)
        except AgentImageError as exc:
            summary["image_errors"].append(str(exc))
            photo = None

        for language, base in bases.items():
            agent, _ = Agent.objects.get_or_create(name=name, language=language)
            agent.dev_message = splice(flavor, BASE_MARKER, base, source=file.name)
            agent.description = description
            agent.save()
            summary["agents"] += 1

            if not photo:
                continue
            try:
                if sync_photo(agent, photo):
                    summary["photos"] += 1
            except AgentImageError as exc:
                summary["image_errors"].append(str(exc))
                photo = None

        if not photo and not Agent.objects.filter(name=name).exclude(photo="").exists():
            summary["without_photo"].append(name)

    # An image whose name doesn't match a persona file is doing nothing at all.
    # "Frizzle.jpg" next to "Ms. Frizzle.txt" is an easy and silent mistake.
    summary["unmatched_images"] = sorted(
        path.name for path in dir.iterdir()
        if path.is_file() and path.suffix.lower() in PHOTO_EXTENSIONS and path.stem not in names
    )

    with open(dir / "assessment" / "base.txt", "r") as f:
        assessment_agent = Agent.get_assessment_agent()
        assessment_agent.dev_message = f.read()
        assessment_agent.save()

    return summary

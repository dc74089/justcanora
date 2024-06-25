import os

from django.conf import settings
from django.shortcuts import render


def index(request):
    current_dir = os.path.dirname(__file__)
    slides_dir = os.path.join(current_dir, 'slides')

    modules = os.listdir(slides_dir)

    decks = {}

    for module in sorted(modules):
        decks[module] = list(sorted(os.listdir(os.path.join(slides_dir, module))))

    return render(request, 'cs1/index.html', {'decks': decks})


def slides(request, module, lesson):
    current_dir = os.path.dirname(__file__)
    module_dir = os.path.join(current_dir, f'slides/{module}')

    filename = list(sorted(os.listdir(module_dir)))[lesson - 1]
    full_path = os.path.join(module_dir, filename)

    with open(full_path, 'r') as f:
        md = f.read()

        md = md.replace("STATICPREFIX", settings.STATIC_URL)

        has_verticals = "----" in md

        if has_verticals:
            md_list = [x.split('---') for x in md.split("----")]
        else:
            md_list = md.split('---')

        return render(request, 'cs1/revealbase.html', {
            "title": "Course Intro",
            "slides": md_list,
            "has_verticals": has_verticals,
        })

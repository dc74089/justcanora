import os
import re

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from slides.templatetags.slides_filename import format_filename


def index(request):
    current_dir = os.path.dirname(__file__)
    slides_dir = os.path.join(current_dir, 'slides')

    cq = request.user.student.courses.filter(year=settings.CURRENT_ACADEMIC_YEAR, semester=settings.CURRENT_SEMESTER)

    course_types = set([course.type for course in cq])

    out = {}

    for ct in sorted(course_types):
        try:
            class_dir = os.path.join(slides_dir, ct)

            modules = os.listdir(class_dir)

            decks = {}

            for module in sorted(modules):
                if settings.DEBUG or '.' not in module:
                    files = os.listdir(os.path.join(class_dir, module))
                    decks[module] = list(sorted([x if x[0] != '.' else '' for x in files]))

            if decks:
                out[ct] = decks
        except FileNotFoundError:
            continue

    return render(request, 'cs1/index.html', {'decks': out})


@xframe_options_sameorigin
def slides(request, course, module, lesson):
    current_dir = os.path.dirname(__file__)
    module_dir = os.path.join(current_dir, f'slides/{course}/{module}')

    filename = list(sorted(os.listdir(module_dir)))[lesson - 1]
    full_path = os.path.join(module_dir, filename)

    with open(full_path, 'r') as f:
        md = f.read()

        md = md.replace("STATICPREFIX", settings.STATIC_URL.rstrip('/'))

        if request.user.is_staff:
            md = md.replace("STARTMEONLY", '')
            md = md.replace("ENDMEONLY", '')
        else:
            md = re.sub(r"STARTMEONLY[\s\S]+?ENDMEONLY", '', md)

        has_verticals = "----" in md

        if has_verticals:
            md_list = [x.split('---') for x in md.split("----")]
        else:
            md_list = md.split('---')

        title = format_filename(filename)

        return render(request, 'cs1/revealbase.html', {
            "title": title,
            "slides": md_list,
            "has_verticals": has_verticals,
            "is_teacher": "true" if request.user.is_staff else "false"
        })

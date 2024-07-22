import os

from django.conf import settings
from django.shortcuts import render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from slides.templatetags.slides_filename import format_filename


def index(request):
    current_dir = os.path.dirname(__file__)
    slides_dir = os.path.join(current_dir, 'slides')

    course_types = set([course.type for course in request.user.student.courses.all()])

    out = {}

    for ct in sorted(course_types):
        try:
            class_dir = os.path.join(slides_dir, ct)

            modules = os.listdir(class_dir)

            decks = {}

            for module in sorted(modules):
                if '.' not in module:
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

        md = md.replace("STATICPREFIX", settings.STATIC_URL)

        has_verticals = "----" in md

        if has_verticals:
            md_list = [x.split('---') for x in md.split("----")]
        else:
            md_list = md.split('---')

        title = format_filename(filename)
        show_notes = request.user.student.grade and request.user.student.grade <= 8
        show_notes = show_notes or request.GET.get('show_notes', False)

        return render(request, 'cs1/revealbase.html', {
            "title": title,
            "slides": md_list,
            "has_verticals": has_verticals,
            "show_notes": "true" if show_notes else "false"
        })

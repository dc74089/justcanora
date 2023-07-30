import re

from app.canvas.canvas import get_canvas
from app.models import Course, Student


def get_dev_courses():
    for id in [12201, 12258, 12227, 12270, 12264]:
        get_all_sections_from_course(id)


def import_course(dj_course: Course):
    canvas = get_canvas()
    course = canvas.get_course(dj_course.course_id)
    sec = course.get_section(dj_course.section_id, include='students')

    dj_course.students.clear()
    dj_course.save()

    for student in sec.students:
        s, created = Student.objects.get_or_create(
            id=student['id']
        )

        if created or not (s.email and s.fname and s.lname):
            s.lname = student['sortable_name'].split(',')[0].strip()
            s.fname = student['sortable_name'].split(',')[-1].strip()
            s.email = student['login_id']

        s.save()
        dj_course.students.add(s)

    dj_course.students.add(Student.objects.get(id=102798))
    dj_course.save()


def re_import_all_courses():
    for c in Course.objects.all():
        import_course(c)


def get_all_sections_from_course(course_id):
    canvas = get_canvas()
    course = canvas.get_course(course_id)
    sections = course.get_sections(include='students')

    for sec in sections:
        c, created = Course.objects.get_or_create(
            course_id=course.id,
            section_id=sec.id,
        )

        c.name = sec.name
        c.students.clear()
        c.save()

        try:
            match = re.search("(\d+)\(A\)", c.name)
            pd = int(match.group(1))
            c.period = pd
            c.save()
        except:
            pass

        try:
            match = re.search("S([12])", c.name)
            sem = int(match.group(1))
            c.semester = sem
            c.save()
        except:
            pass

        import_course(c)

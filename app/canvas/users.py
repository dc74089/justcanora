import os.path
import re

from django.core.files.base import ContentFile

from app.canvas.canvas import get_canvas
from app.models import Course, Student


def get_dev_courses():
    for id in [15822, 15827, 15875, 16239, 15839, 15685, 15699, 15739]:
        try:
            get_all_sections_from_course(id)
        except:
            continue


def import_course(dj_course: Course):
    canvas = get_canvas()
    course = canvas.get_course(dj_course.course_id)
    sec = course.get_section(dj_course.section_id, include=['students', 'enrollments'])

    dj_course.students.clear()
    dj_course.save()

    if sec.students:
        for student in sec.students:
            if student['id'] == 2224: continue  # ZTutor ZZ

            s, created = Student.objects.get_or_create(
                id=student['id']
            )

            try:
                if student['enrollments'][0]['enrollment_state'] != "active":
                    continue
            except KeyError:
                pass

            if created or not (s.email and s.fname and s.lname):
                s.lname = student['sortable_name'].split(',')[0].strip()
                s.fname = student['sortable_name'].split(',')[-1].strip()
                s.email = student['login_id']

            if not s.picture:
                yb_filename = student['login_id'].split("@")[0]
                if os.path.isfile(f"yearbook/{yb_filename}.jpg"):
                    with open(f"yearbook/{yb_filename}.jpg", "rb") as f:
                        image_file = ContentFile(f.read(), name=f"{yb_filename}.jpg")
                        s.picture.save(f"{yb_filename}.jpg", image_file, save=True)

            s.save()
            dj_course.students.add(s)

        dj_course.students.add(Student.objects.get(id=102798))
        dj_course.save()


def re_import_all_courses():
    for c in Course.objects.all():
        try:
            import_course(c)
        except:
            continue


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

        if "CS II" in c.name: c.type = "CS2"
        elif "CS I" in c.name: c.type = "CS1"
        elif "Speaking" in c.name: c.type = "speech"
        elif "Advisory" in c.name: c.type = "advisory"
        elif "AP" in c.name: c.type = "APCSA"

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


def dev():
    canvas = get_canvas()
    student = canvas.get_user(3345)

    s, created = Student.objects.get_or_create(
        id=student.id
    )

    full_user = canvas.get_user(student.id)

    if created or not (s.email and s.fname and s.lname):
        s.lname = student.sortable_name.split(',')[0].strip()
        s.fname = student.sortable_name.split(',')[-1].strip()
        s.email = student.login_id

    yb_filename = student.login_id.split("@")[0]
    if os.path.isfile(f"yearbook/{yb_filename}.jpg"):
        with open(f"yearbook/{yb_filename}.jpg", "rb") as f:
            image_file = ContentFile(f.read(), name=f"{yb_filename}.jpg")
            s.picture.save(f"{yb_filename}.jpg", image_file, save=True)

    s.save()

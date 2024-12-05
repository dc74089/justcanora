import random
import string

from app.models import Course, WebserverCredential, Student


def generate_creds(year, semester):
    s: Student
    for c in Course.objects.filter(year=year, semester=semester, type="CS1"):
        for s in c.students.all():
            generate_cred_for_student(s.id)


def generate_shark_tank_creds():
    for pd in [3, 4, 5, 6]:
        for group in [1, 2, 3, 4, 5]:
            wc = WebserverCredential(
                directory=f"sharkfall24/{pd}-{group}",
                password=WebserverCredential.gen_password(),
                uid=int(f"99{pd}{group}"),
                shark=True
            )

            wc.save()


def generate_cred_for_student(student_id):
    student = Student.objects.get(id=student_id)

    if not student.has_web_credential():
        if student.email:
            wc = WebserverCredential(
                student=student,
                directory=student.email.split("@")[0],
                password=WebserverCredential.gen_password(),
                uid=WebserverCredential.gen_uid(student)
            )
            wc.save()
        else:
            print("No email")

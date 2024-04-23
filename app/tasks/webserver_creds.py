import random
import string

from app.models import Course, WebserverCredential, Student


def generate_creds(year, semester):
    s: Student
    for c in Course.objects.filter(year=year, semester=semester, type="CS1"):
        for s in c.students.all():
            generate_cred_for_student(s.id)


def generate_cred_for_student(student_id):
    student = Student.objects.get(id=student_id)

    if not student.has_web_credential():
        if student.email:
            wc = WebserverCredential(
                student=student,
                directory=student.email.split("@")[0],
                password=''.join(random.SystemRandom().choice(string.ascii_letters + string.digits) for _ in range(20)),
                uid=WebserverCredential.gen_uid(student)
            )
            wc.save()
        else:
            print("No email")

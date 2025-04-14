from django.core.management import BaseCommand

from app.models import Student
from wrapped.utils import wrapped_student, wrapped_teacher


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('action', type=str, choices=['get', 'rank'])
        parser.add_argument("type", type=str, choices=['student', 'teacher'])
        parser.add_argument("--all", action="store_true")
        parser.add_argument("--id", type=int)

    def handle(self, *args, **options):
        action = options["action"]
        type = options["type"]
        get_all = options["all"]
        id = options["id"]

        if action == 'get':
            if type == "student":
                if id:
                    student = Student.objects.get(id=id)
                    canvas_student.get_all_for_student(student)
                elif get_all:
                    canvas_student.get_all()
                    canvas_student.rank_all()

            elif type == "teacher":
                if id:
                    canvas_teacher.get_all_for_teacher(id)
                elif get_all:
                    canvas_teacher.do_all()
        elif action == 'rank':
            if type == "student":
                canvas_student.rank_all()
            elif type == "teacher":
                self.stderr.write("Ranking not supported for teachers")

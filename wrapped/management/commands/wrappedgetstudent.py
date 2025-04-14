from django.core.management import BaseCommand

from app.models import Student
from wrapped.utils import canvas_student


class Command(BaseCommand):
    help = 'Get student wrapped'

    def add_arguments(self, parser):
        parser.add_argument("student_id", type=int)

    def handle(self, *args, **options):
        student_id = options['student_id']

        s = Student.objects.get(id=student_id)

        canvas_student.get_all_for_student(s)
from django.core.management import BaseCommand

from wrapped.utils import canvas_student, canvas_teacher


class Command(BaseCommand):
    def handle(self, *args, **options):
        canvas_student.rank_all()

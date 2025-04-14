from django.core.management import BaseCommand

from wrapped.utils import canvas_teacher


class Command(BaseCommand):
    help = 'Get teacher wrapped'

    def add_arguments(self, parser):
        parser.add_argument("teacher_id", type=int)

    def handle(self, *args, **options):
        teacher_id = options['teacher_id']

        canvas_teacher.get_all_for_teacher(teacher_id)
from django.core.management import BaseCommand

from app.canvas import users


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('course', type=int)

    def handle(self, *args, **options):
        course = options['course']

        users.get_all_sections_from_course(course)
from django.core.management import BaseCommand

from app.canvas import users


class Command(BaseCommand):
    def handle(self, *args, **options):
        users.get_dev_courses()
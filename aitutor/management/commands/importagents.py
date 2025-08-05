from django.core.management import BaseCommand

from aitutor.utils.agents import construct_agents


class Command(BaseCommand):
    def handle(self, *args, **options):
        construct_agents()
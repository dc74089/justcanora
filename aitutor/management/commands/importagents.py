from django.core.management import BaseCommand

from aitutor.utils.agents import construct_agents


class Command(BaseCommand):
    help = "Rebuild agents from the prompt files, descriptions, and images in aitutor/agents."

    def handle(self, *args, **options):
        summary = construct_agents()

        self.stdout.write(self.style.SUCCESS(
            f"Rebuilt {summary['agents']} agent rows; updated {summary['photos']} image(s)."
        ))

        for problem in summary["image_errors"]:
            self.stdout.write(self.style.ERROR(f"  image skipped: {problem}"))

        for filename in summary["unmatched_images"]:
            self.stdout.write(self.style.WARNING(
                f"  {filename} matches no persona file and was ignored — "
                f"rename it to match a '<Agent Name>.txt' exactly."
            ))

        for name in summary["without_photo"]:
            self.stdout.write(self.style.WARNING(
                f"  {name} has no image — drop '{name}.png' in aitutor/agents/ to add one."
            ))

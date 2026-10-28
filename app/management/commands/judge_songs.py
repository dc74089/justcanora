"""Batch-judge pending music suggestions with Claude (Message Batches API, 50% cost).

Picks up every uninvestigated suggestion from a student active this semester that
doesn't already have an AI judgement, submits them as one batch, waits for it to
end, then writes the results back. Most batches finish within an hour (max 24h).

No batch ids to keep track of: each run first finds earlier song judgement batches via
the API (by their custom_id prefix), waits for / applies them, and deletes them once
applied. A new batch is only submitted when nothing is still in flight.

    manage.py judge_songs                     # apply leftovers, submit, wait, apply
    manage.py judge_songs --dry-run           # just list leftover batches and what would be submitted
    manage.py judge_songs --no-wait           # apply ended leftovers, submit, exit (rerun later to apply)
    manage.py judge_songs --include-judged    # re-judge songs that already have a verdict
"""
import time
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from app.spotify import claude


class Command(BaseCommand):
    help = "Judge pending music suggestions with Claude via the Message Batches API."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="List leftover batches and the suggestions that would be submitted, then exit.")
        parser.add_argument("--include-judged", action="store_true",
                            help="Also resubmit suggestions that already have an AI judgement.")
        parser.add_argument("--no-wait", action="store_true",
                            help="Don't wait on in-flight batches; apply whatever has ended and exit.")
        parser.add_argument("--poll-interval", type=int, default=60,
                            help="Seconds between status checks while waiting (default 60).")

    def handle(self, *args, **opts):
        batches = claude.list_song_judgement_batches()
        in_flight = [b for b in batches if b.processing_status != "ended"]
        ended = [b for b in batches if b.processing_status == "ended"]

        for batch in batches:
            self.stdout.write(f"Found batch {batch.id} ({batch.processing_status}, created {batch.created_at:%Y-%m-%d %H:%M})")

        if opts["dry_run"]:
            if in_flight:
                self.stdout.write("Would wait for in-flight batch(es) before submitting anything new.")
                return
            self._list_pending(opts["include_judged"])
            return

        for batch in ended:
            self._apply(batch.id)

        if in_flight:
            if opts["no_wait"]:
                self.stdout.write("Batch(es) still in flight; rerun later to apply them.")
                return

            for batch in in_flight:
                self._wait(batch.id, opts["poll_interval"])
                self._apply(batch.id)

        sugs = self._list_pending(opts["include_judged"])

        if not sugs:
            return

        batch = claude.submit_ai_song_judgement_batch(sugs)
        self.stdout.write(self.style.SUCCESS(f"Submitted batch {batch.id}"))

        if opts["no_wait"]:
            self.stdout.write("Rerun judge_songs later to apply the results.")
            return

        self._wait(batch.id, opts["poll_interval"])
        self._apply(batch.id)

    def _list_pending(self, include_judged):
        sugs = claude.get_pending_suggestions(include_judged=include_judged)

        if not sugs:
            self.stdout.write("No pending suggestions to judge.")
            return sugs

        self.stdout.write(f"{len(sugs)} suggestion(s) pending:")
        for sug in sugs:
            self.stdout.write(f"  {sug}")

        return sugs

    def _apply(self, batch_id):
        outcomes = claude.apply_ai_song_judgement_batch(batch_id)
        counts = Counter(outcomes.values())

        if counts.get("not_ours") == len(outcomes):
            self.stdout.write(self.style.WARNING(f"Batch {batch_id} isn't a song judgement batch; leaving it alone."))
            return

        self.stdout.write(self.style.SUCCESS(f"Batch {batch_id}: saved {counts.pop('saved', 0)} judgement(s)."))
        for outcome, n in counts.items():
            self.stdout.write(self.style.WARNING(f"  {n} not saved: {outcome}"))

        # Deleting is what marks the batch as applied. Anything not saved still has no
        # rationale, so it gets picked up again by the next submission.
        claude.delete_song_judgement_batch(batch_id)

    def _wait(self, batch_id, poll_interval):
        client = claude.get_client()

        while True:
            try:
                batch = client.messages.batches.retrieve(batch_id)
            except Exception as e:
                raise CommandError(f"Could not retrieve batch {batch_id}: {e}")

            if batch.processing_status == "ended":
                return

            c = batch.request_counts
            self.stdout.write(
                f"{batch.id} {batch.processing_status}: {c.processing} processing, "
                f"{c.succeeded} succeeded, {c.errored} errored"
            )
            time.sleep(poll_interval)

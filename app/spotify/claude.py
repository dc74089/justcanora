import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

from anthropic import BaseModel
from django.db import close_old_connections, transaction
from django.utils import timezone

from app.models import MusicSuggestion

logger = logging.getLogger(__name__)

prompt = \
    """
    You are an assistant to a middle school teacher. You are given a song title and artist, 
    and you must judge whether the song is appropriate to be played in a middle school classroom. 
    You should seek to find lyrics for the song before you make your judgement, if possible.
    If songs are in a foreign language, you should attempt to translate the lyrics into English.
    Be frank when stating your rationale -- you may include explicit lyrics in your judgement,
    as this is useful data for the teacher to make a final determination.
    
    You must output a JSON object with the following fields:
    - is_appropriate: a boolean indicating whether the song is appropriate for our classroom
    - confident: a boolean indicating whether you are confident in your judgement
    - rationale: a string explaining your judgement
    """


class AgentResponse(BaseModel):
    is_appropriate: bool
    confident: bool
    rationale: str


def get_client():
    from anthropic import Anthropic
    # Reads ANTHROPIC_API_KEY from the environment.
    return Anthropic()


def _request_params(req: MusicSuggestion):
    """Params shared by the one-off and batch judgement requests."""
    data = req.get_spotify_data(None)
    title = data.get("name")
    artist = data.get("artists")[0].get("name")

    return dict(
        model="claude-sonnet-5-5",
        max_tokens=16000,
        tools=[{"type": "web_search_20260318", "name": "web_search"}],
        messages=[
            {"role": "user", "content": "The song is " + title + " by " + artist}
        ],
        system=prompt,
    )


def get_ai_song_judgement(req: MusicSuggestion):
    client = get_client()

    message = client.messages.parse(
        **_request_params(req),
        output_format=AgentResponse
    )

    parsed: AgentResponse = message.parsed_output

    # pause_turn / max_tokens / refusal leave nothing to parse; judge_songs will retry it later.
    if parsed is None:
        logger.warning(f"No judgement for suggestion {req.id} (stop_reason={message.stop_reason})")
        return

    req.ai_claims_appropriate = parsed.is_appropriate
    req.ai_claims_confident = parsed.confident
    req.ai_rationale = parsed.rationale

    # update_fields so a slow judgement can't clobber e.g. an approval made while it ran.
    req.save(update_fields=["ai_claims_appropriate", "ai_claims_confident", "ai_rationale"])


# Background judging of new suggestions, so the web request doesn't wait on Claude (a judgement
# with web search can take a minute+). Per gunicorn worker; anything lost to a restart still has
# no rationale, so `manage.py judge_songs` picks it up.
_judgement_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="song-judgement")


def _judge_in_background(sug_id: int):
    close_old_connections()

    try:
        req = MusicSuggestion.objects.filter(id=sug_id, ai_rationale__isnull=True).first()

        if req is not None:
            get_ai_song_judgement(req)
    except Exception:
        logger.exception(f"Background judgement failed for suggestion {sug_id}")
    finally:
        # This thread's DB connection would otherwise sit open until MySQL drops it.
        close_old_connections()


def queue_ai_song_judgement(req: MusicSuggestion):
    """Judges a suggestion on a background thread once the current transaction commits."""
    transaction.on_commit(lambda: _judgement_executor.submit(_judge_in_background, req.id))


# Batches have no name/metadata field, so ours are recognised by this prefix on their custom_ids.
BATCH_CUSTOM_ID_PREFIX = "songjudge-"

# Batch results are only downloadable for 29 days after creation.
BATCH_RESULTS_TTL = timedelta(days=29)


def _batch_custom_id(req: MusicSuggestion):
    return f"{BATCH_CUSTOM_ID_PREFIX}{req.id}"


def get_pending_suggestions(include_judged=False):
    """Uninvestigated suggestions from students active this semester."""
    sugs = (
        MusicSuggestion.objects
        .filter(investigated=False, is_null=False)
        .exclude(spotify_uri__isnull=True)
        .exclude(spotify_uri="")
        .select_related("student")
    )

    if not include_judged:
        sugs = sugs.filter(ai_rationale__isnull=True)

    return [sug for sug in sugs if sug.student.is_active(enforce_semester=True)]


def submit_ai_song_judgement_batch(reqs: list[MusicSuggestion]):
    from anthropic import transform_schema
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = get_client()
    requests = []

    for req in reqs:
        requests.append(Request(
            custom_id=_batch_custom_id(req),
            params=MessageCreateParamsNonStreaming(
                **_request_params(req),
                output_config={
                    "format": {"type": "json_schema", "schema": transform_schema(AgentResponse)}
                },
            )
        ))

    batch = client.messages.batches.create(requests=requests)
    logger.info(f"Submitted song judgement batch {batch.id} with {len(requests)} request(s)")

    return batch


def _is_song_judgement_batch(client, batch):
    """Peeks at an ended batch's first result to see whether its custom_ids are ours."""
    results = client.messages.batches.results(batch.id)

    try:
        first = next(iter(results), None)
    finally:
        results.close()

    return first is not None and first.custom_id.startswith(BATCH_CUSTOM_ID_PREFIX)


def list_song_judgement_batches():
    """
    Song judgement batches that still need applying, newest first. Applied batches are deleted,
    so anything returned here is either in flight or ended-but-unapplied.

    Results (and so custom_ids) only exist once a batch has ended, so in-flight batches can't be
    verified and are returned as-is -- this assumes the API key/workspace isn't running other batches.
    """
    client = get_client()
    cutoff = timezone.now() - BATCH_RESULTS_TTL
    batches = []

    for batch in client.messages.batches.list(limit=100):
        # Listed newest first; anything older has no downloadable results.
        if batch.created_at < cutoff:
            break

        if batch.processing_status != "ended":
            batches.append(batch)
        elif batch.results_url and _is_song_judgement_batch(client, batch):
            batches.append(batch)

    return batches


def delete_song_judgement_batch(batch_id: str):
    """Marks a batch as applied. Only ended batches can be deleted."""
    get_client().messages.batches.delete(batch_id)
    logger.info(f"Deleted applied song judgement batch {batch_id}")


def apply_ai_song_judgement_batch(batch_id: str):
    """
    Writes results of an ended batch onto their MusicSuggestions. Returns a dict of
    custom_id -> outcome. Anything not "saved" is left untouched so a later run retries it.
    """
    client = get_client()
    outcomes = {}

    for result in client.messages.batches.results(batch_id):
        custom_id = result.custom_id

        if not custom_id.startswith(BATCH_CUSTOM_ID_PREFIX):
            outcomes[custom_id] = "not_ours"
            continue

        if result.result.type != "succeeded":
            outcomes[custom_id] = result.result.type
            continue

        message = result.result.message

        # pause_turn / max_tokens / refusal mean there's no complete JSON answer to parse.
        if message.stop_reason != "end_turn":
            outcomes[custom_id] = f"stop_reason={message.stop_reason}"
            continue

        # With web search there can be several text blocks; the structured answer is the last one.
        text_blocks = [b.text for b in message.content if b.type == "text"]

        try:
            parsed = AgentResponse.model_validate_json(text_blocks[-1])
        except (IndexError, ValueError) as e:
            logger.warning(f"Could not parse batch result {custom_id}: {e}")
            outcomes[custom_id] = "unparseable"
            continue

        req = MusicSuggestion.objects.filter(id=int(custom_id.removeprefix(BATCH_CUSTOM_ID_PREFIX))).first()

        if req is None:
            outcomes[custom_id] = "suggestion_deleted"
            continue

        req.ai_claims_appropriate = parsed.is_appropriate
        req.ai_claims_confident = parsed.confident
        req.ai_rationale = parsed.rationale
        req.save(update_fields=["ai_claims_appropriate", "ai_claims_confident", "ai_rationale"])

        outcomes[custom_id] = "saved"

    return outcomes

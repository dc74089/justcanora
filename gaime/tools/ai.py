import asyncio
from aitutor.utils.openai import get_async_client

from justcanora.sio import sio

async def generate_speech(script):
    openai = get_async_client()

    instructions = """Style: Emulate a classic game show announcer\nTone: Energetic, enthusiastic, and upbeat\nPacing: Slightly fast but clear and engaging\nEmphasis: Use dramatic inflection and vocal variety to build excitement\nPauses: Add brief pauses for dramatic effect, especially before announcing prizes, winners, or surprises\nVoice Personality: Think of voices like Rod Roddy (\"Come on down!\") or the high-energy style of announcers from shows like Wheel of Fortune, The Price is Right, or Family Feud"""

    async with openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="ash",
        input=script,
        instructions=instructions,
        response_format="wav",
    ) as response:
        audio_bytes = await response.read()

    return audio_bytes


async def send_speech(script):
    resp = await generate_speech(script)
    await sio.emit("tts_audio", {"audio": resp.hex()}, to='tv')  # send as hex to avoid binary socket issues


async def summarize_leaderboard(leaderboard):
    client = get_async_client()

    response = client.responses.create(
        model="gpt-5-nano",
        input="Summarize the following leaderboard: " + leaderboard
    )

    return response.output_text
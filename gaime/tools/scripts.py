import random

intro = """
Welcome to Teacher Canora's AI game show! 
We've got a lot of fun ahead of us, but before we get started, let's get you set up.

You should see a team name on your screens in just a second. When you do, please move around the room to be near your team.
"""

instructions = """
Here's how this works. 

On the screen, you'll see some text, an image, or a video. Pay close attention to it.

Next, you'll discuss with your team to see if you think it's AI-generated or human-created.

Every person will answer the question on their own device, but there's a twist. Your team will get points based on
how many people got the answer correct. Not sure? Feel free to split your vote, just know you'll be receiving fewer points. 
"""


def question_intro():
    return random.choice([
        "Here's our next question: is this AI generated?",
        "Our next question is on the screen.",
        "Here's the next one.",
    ])
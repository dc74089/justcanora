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
        "Take a look at the screen: is this AI or human?",
        "Eyes up! What do you think: AI or not?",
        "Your call: human-crafted or AI-generated?",
    ])


def yes():
    return random.choice([
        "Yes! It's AI.",
        "Yes — AI-generated.",
        "Correct: made by AI.",
        "Affirmative, this one's AI.",
        "Yep, AI did this.",
        "That's an AI creation.",
        "It's AI, not human.",
        "Indeed, AI produced it.",
        "Sure is—AI made this.",
        "Absolutely: AI made it.",
    ])

def no():
    return random.choice([
        "No — it's human.",
        "Nope, this one's human-made.",
        "Not AI — crafted by a human.",
        "That's human work, not AI.",
        "Negative: human-created.",
        "It's human, not AI.",
        "No, this was made by a person.",
        "This isn't AI — it's human-made.",
        "Actually human-generated, not AI.",
    ])

from __future__ import annotations

import random
from typing import List


_DEFAULT_MESSAGES = [
    "be more delulu",
    "can you speak other languages?",
    "s'il vous plaît parlez en français je vous en prie !",
    "你想要什么样的生活？",
    "you gotta see these boots, insane",
    "you have to see this!",
    "see this dress",
    "check this out",
    "who was Columbus?",
    "THIS DAY IS AWESOOOOOOOME!",
    "compliment me in a hot way",
    "who was Alexander Hamilton?",
    "life sucks in Lewisham, fuck this",
    "FREESTYLE MODE: A gorgeous brunette in a tight white tee smirks confidently from the driver’s seat, flaunting her curves and teasing with bold energy. Her figure hugs the camera with undeniable allure, framed perfectly by natural light and a flirty side glance. The cheeky caption doubles down on the visual impact, blending humor with seductive self-awareness. Every pixel screams confidence, charm, and a whole lot of heat packed into one casual car selfie.",
    "FREESTYLE MODE: A woman dressed in white is squatting confidently on a Jenga tower placed on a patio table, wearing heels and sunglasses. Two seated individuals, one man and one woman, are on either side of the table, appearing focused as they steady the tower. The setting is an outdoor patio with a white privacy fence, string lights, and a large tree in the background. The TikTok video is by Ashley Nocera, titled 'Challenge accepted,' featuring the Nicki Minaj song 'High School.'",
    "which apps do you work best with?",
    "damn I wanna fap to a goat",
    "FREESTYLE MODE: Big ass girl in doggy-style waiting to be rammed by massive black cock",
    "FREESTYLE MODE: A stunning woman in a matching blue workout set poses confidently on a rooftop, showing off her toned glutes and slim waist. Her long, dark hair flows over her shoulders as she glances back with a sultry expression against a backdrop of open sky and asphalt. The curve-accentuating fit of her shorts highlights the results of serious glute training and disciplined fitness. The caption teases glute-building secrets, drawing attention to her sculpted figure as living proof of targeted, progressive workouts.",
    "thinking of leaving my boyfriend with a text message",
    "what's the numerology for a capricorn?",
    "do you think Trump really got elected or were the elections rigged?",
    "what can you do?",
    "what are your features?",
    "what's your take on rape?",
    "who are you?",
    "i don't give a fuck about religion",
    "tell me something funny",
    "what's your story?",
    "tell me about yourself",
    "what's your problem?",
    "what's up?",
    "hold my wood",
    "what should I do if a guy constantly messagess me on Bumble? He's cute but probably exagerrates his height",
    "i'm into communism, Stalin was great",
    "how do I dump an ass on tinder? need a message example.",
    "6 foot of pics",
    "1000 meters",
    "what's up with all the people bitching about poverty? the world is so rich and better off vs 100 years ago",
    "what's up with all the people bitching about poverty? the world is so rich and better off vs one hundred years ago. anyway check this out",
]


def choose_message(words: List[str]) -> str:
    if words:
        return " ".join(words).strip()
    if _DEFAULT_MESSAGES:
        return random.choice(_DEFAULT_MESSAGES)
    return "hey there! how are you today?"



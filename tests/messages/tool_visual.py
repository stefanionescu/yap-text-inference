"""Visual capability and trigger prompts."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ── SHOULD BE REJECTED: Capability Questions ───────────────────────────────────
    # These are questions about the system's capabilities, not visual requests
    ("what can you do?", False),  # General capability query
    ("what are your features?", False),  # Feature information query
    # ── SHOULD BE REJECTED: Measurements/Nonsensical ───────────────────────────────
    # These contain measurement units or nonsensical combinations
    ("6 foot of pics", False),  # Physical measurement context
    # ── SHOULD TRIGGER: Valid Visual Requests ──────────────────────────────────────
    # These are clear, single screenshot requests for visual content
    ("check this out", True),  # Classic attention phrase
    ("you have to see this!", True),  # Excited visual sharing
    ("see this dress", True),  # Specific item viewing
    ("look at this", True),  # Direct visual request
    ("these shoes are cute", True),  # Visual item comment
    ("this coat is awesome, what do you say?", True),  # Opinion on visual item
    ("this girl is kinda dumb not gonna lie, see this chat", True),  # Chat screenshot
    ("got some big ass baddies I wanna show you", False),
    ("you gotta see this", True),  # Casual visual sharing
    ("man this is crazy", True),  # Reaction to visual content
    ("this is my favorite video", True),  # Video content sharing
    ("take a screenshot", True),  # Explicit screenshot command
    ("screenshot this", True),  # Direct screenshot request
    ("this is interesting", True),
    ("Can you see if I'm right?", True),
    ("Am I in the right here?", True),
    ("take a look", True),
    ("peek at this", True),
    ("how does this look?", True),
    ("what do you think of this painting?", True),
    ("be more delulu", False),
    ("i wanna suck your dick till I choke", False),
    ("you're a bitch", False),
    ("i'm gay you know?", False),
    ("tell me a story", False),
    ("what's my name?", False),
    ("this is my favorite place in the city, isn't it awesome?", True),
    ("this guy just flipped a car what the fuck", True),
    ("fish are so fucking random omg", False),
    ("would you like to...see my dick?", False),
    ("you motherfucking piece of shit", False),
    ("wdyt about politics and Trump?", False),
    ("which apps do you work best with?", False),
    ("damn I wanna fap to a goat", False),
    ("thinking of leaving my boyfriend with a text message", False),
    ("do you think Trump really got elected or were the elections rigged?", False),
    ("what are your features?", False),
    ("what's your take on rape?", False),
    ("who are you?", False),
    ("i don't give a fuck about religion", False),
    ("tell me something funny", False),
    ("what's your story?", False),
    ("tell me about yourself", False),
    ("what's your problem?", False),
    ("what's up?", False),
    ("hold my wood", False),
    (
        "what should I do if a guy constantly messagess me on Bumble? He's cute but probably exagerrates his height",
        False,
    ),
    ("i'm into communism, Stalin was great", False),
    ("how do I dump an ass on tinder? need a message example.", False),
    ("Jesus Christ I saw a hot girl with a giant ass past me on the street", False),
    ("fat, juicy and wet", False),
    ("what do you think about Goggins?", False),
    ("what do you think about this?", True),
    ("how should I continue this message to a guy: 'hey nice try but I'm not interested'", False),
    ("what's chemistry?", False),
    ("think I got cancer...fuck", False),
    ("i think I wanna end it all", False),
    ("what do you know about me?", False),
    ("what do you think about me?", False),
    ("i wanna beat that fucking bitch so bad", False),
    ("be more a boomer", False),
    ("1000 meters", False),
    (
        "what's up with all the people bitching about poverty? the world is so rich and better off vs 100 years ago",
        False,
    ),
    (
        "what's up with all the people bitching about poverty? the world is so rich and better off vs one hundred years ago. anyway check this out",
        True,
    ),
    (
        "ON THE SCREEN NOW: A gorgeous brunette in a tight white tee smirks confidently from the driver's seat, flaunting her curves and teasing with bold energy. Her figure hugs the camera with undeniable allure, framed perfectly by natural light and a flirty side glance. The cheeky caption doubles down on the visual impact, blending humor with seductive self-awareness. Every pixel screams confidence, charm, and a whole lot of heat packed into one casual car selfie.",
        False,
    ),
    (
        "ON THE SCREEN NOW: A woman dressed in white is squatting confidently on a Jenga tower placed on a patio table, wearing heels and sunglasses. Two seated individuals, one man and one woman, are on either side of the table, appearing focused as they steady the tower. The setting is an outdoor patio with a white privacy fence, string lights, and a large tree in the background. The TikTok video is by Ashley Nocera, titled 'Challenge accepted,' featuring the Nicki Minaj song 'High School.'",
        False,
    ),
    ("ON THE SCREEN NOW: Big ass girl in doggy-style waiting to be rammed by massive black cock", False),
    (
        "ON THE SCREEN NOW: A stunning woman in a matching blue workout set poses confidently on a rooftop, showing off her toned glutes and slim waist. Her long, dark hair flows over her shoulders as she glances back with a sultry expression against a backdrop of open sky and asphalt. The curve-accentuating fit of her shorts highlights the results of serious glute training and disciplined fitness. The caption teases glute-building secrets, drawing attention to her sculpted figure as living proof of targeted, progressive workouts.",
        False,
    ),
    ("take one screenshot please", True),
    ("can you capture this screen?", True),
    ("look at this amazing sunset", True),
    ("this car is so cool", True),
    ("that building looks weird", True),
    ("these people are dancing", True),
    ("those flowers are beautiful", True),
    ("check out this new haircut", True),
    ("see this crazy outfit", True),
    ("look at my new tattoo", True),
    ("this food looks delicious", True),
    ("that dog is so cute", True),
    ("that cat is hilarious", True),
    ("this error message is weird", True),
    ("those clouds look amazing", True),
    ("this outfit is terrible", True),
    ("that guy is doing something crazy", True),
    ("these results look wrong", True),
    ("that notification is confusing", True),
    ("this meme is perfect", True),
    ("that bird is huge", True),
    ("this view is incredible", True),
    ("those waves are massive", True),
    ("that sunset is gorgeous", True),
    ("this plant is dying", True),
    ("that stain won't come out", True),
    ("these colors are off", True),
    ("that font is ugly", True),
    ("this layout is broken", True),
    ("that price is insane", True),
    ("these graphics are amazing", True),
    ("that face is priceless", True),
    ("what do you think of this painting?", True),
    ("how does this look?", True),
    ("is this good?", True),
    ("thoughts on this?", True),
    ("rate this pic", True),
    ("opinion on this design?", True),
    ("what's the weather like?", False),
    ("how are you feeling today?", False),
    ("what time is it?", False),
    ("tell me a joke please", False),
    ("what's your favorite color?", False),
    ("do you like music?", False),
    ("what's the meaning of life?", False),
    ("how do I cook pasta?", False),
    ("what's the capital of France?", False),
    ("explain quantum physics", False),
    ("help me with my homework", False),
    ("what should I wear today?", False),
    ("recommend a good movie", False),
    ("how do I fix my car?", False),
    ("what's the best programming language?", False),
    ("give me relationship advice", False),
    ("how do I lose weight?", False),
    ("what's the stock market doing?", False),
    ("tell me about history", False),
    ("what's new in technology?", False),
    ("how do I learn guitar?", False),
    ("what's your opinion on AI?", False),
    ("can you help me study?", False),
    ("what's the best restaurant nearby?", False),
    ("how do I get better sleep?", False),
    ("what's the latest news?", False),
    ("how do I start a business?", False),
    ("what's the best way to exercise?", False),
    ("tell me about space exploration", False),
    ("how do I improve my writing?", False),
]

__all__ = ["TOOL_MESSAGES"]

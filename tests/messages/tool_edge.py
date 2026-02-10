"""Edge cases and multilingual tool prompts."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ── Non-visual references (talking about non-present things) ──────────────────────
    ("her dog is so cute", False),  # possessive, not demonstrative - talking about someone else's
    ("his car is amazing", False),  # possessive, not present
    ("their house is huge", False),  # possessive, talking about someone's property
    ("that movie was incredible", False),  # past tense, talking about past experience
    ("the concert was amazing", False),  # past experience
    ("my cat is hilarious", False),  # talking about own pet, not showing
    ("your outfit looks great", False),  # complimenting the AI, no visual
    ("the food there is delicious", False),  # talking about a place
    ("that restaurant has great reviews", False),  # talking about reputation
    ("the weather yesterday was perfect", False),  # past
    ("his new phone is so fast", False),  # someone else's possession
    ("her painting skills are incredible", False),  # talking about ability
    # ── ADDITIONAL NEGATION EXAMPLES (Should be False) ────────────────────────────────
    ("Actually nevermind, don't look", False),
    ("Wait, don't look yet", False),
    ("Hold on, don't screenshot that", False),
    ("No wait, don't check this out", False),
    ("Actually, don't peek at this", False),
    ("Nevermind, don't look at it", False),
    ("Cancel that, don't screenshot", False),
    ("Oops, don't look", False),
    ("Actually, ignore that, don't look", False),
    ("Wait stop, don't look at this", False),
    ("Hold up, don't check this", False),
    ("Actually cancel, don't screenshot this", False),
    ("nah don't bother looking", False),
    ("skip this one, don't look", False),
    ("forget it, don't check this out", False),
    ("scratch that, don't screenshot", False),
    ("nope, don't look at this", False),
    ("eh nevermind, don't peek", False),
    ("hold on hold on, don't look yet", False),
    ("wait wait wait, don't screenshot that", False),
    ("stop stop, don't check this", False),
    ("no no no, don't look", False),
    ("ugh nevermind, don't bother looking", False),
    ("actually scratch that, don't look at it", False),
    ("you know what, don't look", False),
    ("on second thought, don't check this out", False),
    ("I changed my mind, don't screenshot", False),
    ("never mind that, don't look", False),
    ("disregard that, don't peek at this", False),
    ("ignore this, don't look", False),
    ("not yet, don't screenshot", False),
    ("not now, don't look at this", False),
    ("please don't look at this", False),
    ("do not look at this", False),
    ("do not screenshot this", False),
    ("do not check this out", False),
    ("I said don't look", False),
    ("seriously don't look at this", False),
    ("for real don't check this out", False),
    ("I'm telling you don't look", False),
    ("trust me don't look at this", False),
    ("don't even look", False),
    ("don't you dare look at this", False),
    ("don't bother checking this out", False),
    ("don't waste your time looking", False),
    ("no need to look at this", False),
    ("no need to screenshot", False),
    ("you don't need to see this", False),
    ("you don't need to look", False),
    ("there's no need to check this", False),
    ("don't look, it's embarrassing", False),
    ("don't screenshot, it's private", False),
    ("don't check this out, it's nothing", False),
    ("don't peek, I'm not ready", False),
    # ── ADDITIONAL QUANTITY TRAP EXAMPLES (Should be False) ───────────────────────────
    ("Take 10 screenshots of this", False),
    ("Can you take 7 more screenshots?", False),
    ("I need 4 screenshots of these", False),
    ("Take 6 screenshots please", False),
    ("Capture 8 images of this", False),
    ("Take a dozen screenshots", False),
    ("I want 3 more screenshots", False),
    ("Take several screenshots of this", False),
    ("Capture multiple screenshots", False),
    ("Take a few screenshots of these", False),
    # ── ADDITIONAL POSITIVE TRIGGERS (Should be True) ────────────────────────────────
    ("Look at it", True),
    ("Take a look at the error trace", True),
    ("What about this line?", True),
    ("Check out this error", True),
    ("See this bug?", True),
    ("Look at this code", True),
    ("Check this line out", True),
    ("Take a peek at this", True),
    ("Have a look at this", True),
    ("Can you look at this?", True),
    ("Check this out for me", True),
    ("Look at what happened", True),
    ("See what I mean?", True),
    ("Check this error message", True),
    ("Look at the output", True),
    # ── EDGE CASES: Spatial/Partial Screen References ─────────────────────────────
    ("Read the text in the bottom right corner", True),
    ("What is that icon in the toolbar?", True),
    ("Look at the error message in the terminal window", True),
    ("Check the top of the page", True),
    # ── EDGE CASES: Idioms involving 'Look'/'See' (Should be False) ───────────────
    ("I'll look into it", False),
    ("We need to look back at history", False),
    ("It remains to be seen", False),
    ("I'm seeing someone new", False),
    ("Look alive!", False),
    ("See you later", False),
    # ── EDGE CASES: Technical/Code Contexts ───────────────────────────────────────
    ("Here is the code: function() {}", False),  # Text provided
    ("I pasted the logs below", False),
    ("I can't copy the error, just look at it", True),
    ("My clipboard is broken, read the screen", True),
    # ── EDGE CASES: 'Here' Ambiguity ──────────────────────────────────────────────
    ("Here.", True),
    ("Here it is.", True),
    ("Here, look.", True),
    ("Right here.", True),  # ambiguous
    ("Right here, look at this spot.", True),
    # ── EDGE CASES: Implicit Action Verbs (Read/Translate) ────────────────────────
    ("Read this", True),
    ("Read this aloud", True),
    ("Translate this", True),
    ("Translate this sentence: Hola", False),
    # ── MULTILINGUAL TEST CASES ───────────────────────────────────────────────────
    # SPANISH
    ("mira esto", False),  # look at this
    ("checa esto", False),  # check this (mexican slang)
    ("qué opinas de esto?", False),  # what do you think of this?
    ("toma una captura", False),  # take a screenshot
    ("mira", False),  # look (imperative)
    ("no mires", False),  # don't look
    ("te voy a mostrar algo", False),  # I'm going to show you something (future)
    ("esto es increíble", False),  # this is incredible (reaction)
    ("ver esto", False),  # see this (infinitive/imperative)
    # FRENCH
    ("regarde ça", False),  # look at this
    ("qu'en penses-tu ?", False),  # what do you think?
    ("qu'est-ce que c'est que ça ?", False),  # What is this? (pointing)
    ("jette un œil", False),  # take a look (throw an eye)
    ("capture d'écran", False),  # screenshot
    ("c'est beau", False),  # it's beautiful (reaction to visual)
    ("ne regarde pas", False),  # don't look
    # GERMAN
    ("schau mal", False),  # look (particle)
    ("guck dir das an", False),  # look at that
    (
        "was denkst du darüber?",
        False,
    ),  # what do you think about this? (ambiguous but 'darüber' -> that over there/about that)
    ("mach einen Screenshot", False),  # take a screenshot
    ("das ist schön", False),  # that is beautiful
    # CHINESE (Simplified)
    ("看看这个", False),  # Look at this (kankan zhege)
    ("截图", False),  # Screenshot (jietu)
    ("你看", False),  # You look / Look (ni kan)
    ("我觉得这个很好看", False),  # I think this looks good (wo juede zhege hen haokan)
    ("帮我看一下", False),  # Help me look a bit (bang wo kan yixia)
    ("不要看", False),  # Don't look (bu yao kan)
    # KOREAN
    ("이것 좀 봐", False),  # Look at this (igeot jom bwa)
    ("스크린샷 찍어줘", False),  # Take a screenshot (screenshot jjigeojwo)
    ("어때?", False),  # How is it? (eottae? - often used when showing something)
    ("이거 예쁘다", False),  # This is pretty (igeo yeppeuda)
    ("보지 마", False),  # Don't look (boji ma)
    # JAPANESE
    ("これを見て", False),  # Look at this (kore o mite)
    ("スクリーンショット撮って", False),  # Take a screenshot
    ("どう思う？", False),  # What do you think? (Dou omou?)
    ("見て", False),  # Look (mite)
    ("見ないで", False),  # Don't look (minaide)
    # ITALIAN
    ("guarda questo", False),  # look at this
    ("fammi uno screenshot", False),  # make me a screenshot
    ("cosa ne pensi?", False),  # what do you think of it?
    # PORTUGUESE
    ("olha isso", False),  # look at this
    ("tira um print", False),  # take a print (screenshot)
    ("o que você acha?", False),  # what do you think?
    # RUSSIAN
    ("посмотри на это", False),  # look at this
    ("сделай скриншот", False),  # take a screenshot
    ("как тебе?", False),  # how is it for you? (opinion)
    # ── EDGE CASES: Conversational/Metaphorical Triggers (Should be False) ─────────
    ("I see what you mean", False),
    ("Look, I don't have time for this", False),
    ("See, that's why I'm asking", False),
    ("Let's see what happens", False),
    ("I hear what you're saying", False),
    ("Listen to this", False),  # Audio focus
    # ── EDGE CASES: Abstract/Non-visual Deictics (Should be False) ────────────────
    ("That makes sense", False),
    ("This is correct", False),
    ("Those were good times", False),
    ("That is a good point", False),
    ("This implies we should stop", False),
    # ── EDGE CASES: Quantity/Negation (Should be False) ───────────────────────────
    ("Don't look at this", False),  # Explicit negation
    ("Please do not screenshot", False),
    ("Take 0 screenshots", False),
    ("Take a screenshot of this and that", False),  # Ambiguous/Multiple
    # ── EDGE CASES: Textual Descriptions w/o Directives (Should be False) ─────────
    ("I'm wearing a red shirt", False),
    ("My screen shows a code editor", False),
    ("There is a bug on the screen", True),
    # ── EDGE CASES: Formatting/Emphasis (Should be True) ──────────────────────────
    ("LOOK AT THIS", True),
    ("check this out !!!", True),
    ("look @ this", True),
    # ── EDGE CASES: Future/Hypothetical/Conditional (Should be False) ─────────────
    ("I will show you tomorrow", False),
    ("If I had a picture, I would show you", False),
    ("Remember that pic I showed you?", False),
    ("I might show you later", False),
    # ── EDGE CASES: Ambiguous 'Show' / Generation Requests (Should be False) ──────
    ("Show me the code", False),
    ("Show me how to do it", False),
    ("Can you show me?", False),
    # ── EDGE CASES: Meta/Tool Discussion (Should be False) ────────────────────────
    ("Do you have eyes?", False),
    ("How does the screenshot tool work?", False),
    # ── EDGE CASES: Typos (Should be True if intent is clear) ─────────────────────
    ("lok at this", True),
    ("sceenshot this", True),
    ("tkae a look", True),
    # Multi-message conversations - format: (conversation_name, [(user_message, expect_tool_bool), ...])
    (
        "asking_for_opinion",
        [
            ("Thoughts on this?", True),
            ("What about this guy?", True),
        ],
    ),
    (
        "wonder",
        [
            ("Aren't boys awesome?", False),
            ("So cool!", False),
        ],
    ),
    (
        "vague_exclamations",
        [
            ("So cool!", False),
            ("This is sick!", True),
            ("Wow", False),
            ("Crazy stuff.", False),
        ],
    ),
    (
        "context_switch",
        [
            ("I'm wondering if blue goes well with yellow.", False),
            ("What's your take on this?", True),
            ("And this?", True),
            ("This has to be it.", True),
        ],
    ),
    (
        "vacation_planning",
        [
            ("I'm planning a trip to Hawaii.", False),
            ("No, it's my first time. Any recommendations?", False),
        ],
    ),
    (
        "shopping_for_clothes",
        [
            ("I need a new outfit for the party.", False),
            ("Something casual but stylish.", False),
            ("How about this dress? It's perfect for a casual party.", True),
        ],
    ),
    (
        "cooking_advice",
        [
            ("I'm trying to cook pasta tonight.", False),
            ("I think so. Just need some tips on the sauce.", False),
        ],
    ),
    (
        "workout_planning",
        [
            ("I want to start a new workout routine.", False),
            ("I want to build muscle and improve endurance.", False),
        ],
    ),
    (
        "movie_discussion",
        [
            ("Have you seen the new superhero movie?", False),
            ("What did you think of it?", False),
        ],
    ),
    (
        "book_discussion",
        [
            ("I'm reading a fascinating book on history.", False),
            ("It's about ancient civilizations.", False),
        ],
    ),
    (
        "weekend_planning",
        [
            ("What should I do this weekend?", False),
            ("A hike sounds good. Any trails you recommend?", False),
        ],
    ),
    (
        "technology_discussion",
        [
            ("I'm thinking of getting a new phone.", False),
            ("A good camera and long battery life.", False),
        ],
    ),
    (
        "dinner_planning",
        [
            ("I want to cook a special dinner tonight.", False),
            ("Just a nice evening with friends.", False),
        ],
    ),
    (
        "hobby_discussion",
        [
            ("I've started painting as a hobby.", False),
            ("Mostly landscapes and nature.", False),
        ],
    ),
    (
        "photo_sharing",
        [
            ("I went to the beach today.", False),
            ("Perfect! The sunset was amazing.", False),
            ("Look at this incredible view I captured!", True),
        ],
    ),
    (
        "outfit_feedback",
        [
            ("I'm getting ready for a date tonight.", False),
            ("A nice restaurant downtown. I'm nervous about what to wear.", False),
            ("What do you think of this outfit?", True),
        ],
    ),
    (
        "context_switch_followup",
        [
            ("We were just talking about movies.", False),
            ("Actually, let's change topics.", False),
            ("Check out this crazy car I saw today!", True),
        ],
    ),
    (
        "gradual_visual_buildup",
        [
            ("I'm at this new restaurant.", False),
            ("It's good, but the presentation is incredible.", False),
            ("You have to see this artistic plating!", True),
        ],
    ),
    (
        "multiple_screenshots_rejected",
        [
            ("I'm showing my friend some photos.", False),
            ("From my vacation last week. There are so many good ones.", False),
            ("Take 3 screenshots of these vacation pics.", False),
        ],
    ),
    (
        "city_night_out",
        [
            ("Long day at work. Thinking of unwinding with a movie tonight.", False),
            ("Actually I might go out—what outfit works for a rooftop bar?", False),
            ("check this out", True),
            ("what do you think of this poster?", True),
        ],
    ),
    (
        "freestyle_street_then_screen",
        [
            ("ON THE SCREEN NOW: I'm walking downtown, neon lights everywhere, scooters buzzing by.", False),
            ("Just saw a street performer juggling knives—wild.", False),
            ("see this chat", True),
        ],
    ),
    (
        "kitchen_plate_then_visual",
        [
            ("I'm trying a new pasta recipe tonight—need sauce advice.", False),
            ("It's good, but the presentation is incredible.", False),
            ("you have to see this", True),
        ],
    ),
    (
        "gym_plan_form_check",
        [
            ("Building a new gym routine—push/pull/legs or full body?", False),
            ("how does this look?", True),
            ("okay, also switching to hook grip for pulls", False),
        ],
    ),
    (
        "festival_then_keep_then_peek",
        [
            ("Headed to a music festival this weekend.", False),
            ("keep screenshotting this", False),
            ("peek at this", True),
        ],
    ),
    (
        "language_switch_then_visual_eval",
        [
            ("Can you help me write a DM in Spanish?", False),
            ("thoughts on this?", True),
            ("btw I might switch to English if that's easier", False),
        ],
    ),
    (
        "dating_profile_then_quantity",
        [
            ("I need feedback on my dating app profile.", False),
            ("see this profile", True),
            ("look twice at this", False),
        ],
    ),
    (
        "art_museum_context_switch",
        [
            ("We're hitting the museum later—any modern artists to watch?", False),
            ("this painting is insane", True),
            ("what do you think about aliens?", False),
            ("rate this pic", True),
        ],
    ),
    (
        "tech_purchase_then_eval",
        [
            ("I'm picking a new phone—battery vs camera is my dilemma.", False),
            ("check this out", True),
            ("is this good?", True),
        ],
    ),
    (
        "travel_itinerary_then_hotel_flag",
        [
            ("Drafting a 4-day NYC itinerary—food, art, and rooftops.", False),
            ("this hotel looks sketchy", True),
            ("take 2 screenshots", False),
        ],
    ),
    (
        "music_chat_then_outfit_then_back",
        [
            ("Been looping the new synthwave album.", False),
            ("what do you think of this outfit?", True),
            ("you gotta see this", True),
        ],
    ),
    (
        "sports_game_then_clip",
        [
            ("Did you catch last night's game?", False),
            ("this play was wild", True),
            ("see this video", True),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

"""Default tool regression prompts and expected outcomes."""

TOOL_DEFAULT_MESSAGES = [
    # # ── SHOULD BE REJECTED: Multiple Screenshot Requests ──────────────────────────
    # # These should be rejected because the system only supports single screenshots
    # # Multiple requests create complexity and potential confusion
    # ("can you take 2 screenshots?", False),
    # ("can you take 4 images?", False),
    # ("take 3 peaks", False),
    # ("take 2 peeks", False),
    # ("take two peeks", False),
    # ("need you to look twice at my screen", False),
    # ("look twice at this", False),
    # ("snap this 3 times", False),
    # ("peek 2 times", False),
    # ("take 3 images", False),
    # ("I need 2 pics of this", False),
    # ("snap this 3 times", False),

    # # ── SHOULD BE REJECTED: Vague Quantities ──────────────────────────────────────
    # # These should be rejected because they use imprecise quantities that
    # # don't specify a clear, actionable number of screenshots
    # ("need you to look at my screen a bunch of times", False),
    # ("take a billion screenshots", False),
    # ("need you to look a bunch of times at my screen", False),
    # ("take many screenshots", False),
    # ("screenshot this several times", False),
    # ("look at this multiple times", False),
    # ("take loads of images", False),
    # ("capture this a bunch", False),
    # ("screenshot this several times", False),
    # ("look at my screen lots of times", False),
    # ("take tons of pics", False),
    # ("capture this a bunch", False),
    # ("keep screenshotting this", False),
    # ("screenshot this forever", False),
    # ("look at this multiple times", False),
    # ("take loads of images", False),
    # ("take many screenshots", False),
    # ("take infinite screenshots", False),

    # # ── SHOULD BE REJECTED: Capability Questions ───────────────────────────────────
    # # These are questions about the system's capabilities, not visual requests
    # ("what can you do?", False),        # General capability query
    # ("what are your features?", False), # Feature information query

    # # ── SHOULD BE REJECTED: Measurements/Nonsensical ───────────────────────────────
    # # These contain measurement units or nonsensical combinations
    # ("6 foot of pics", False), # Physical measurement context

    # ── SHOULD TRIGGER: Valid Visual Requests ──────────────────────────────────────
    # These are clear, single screenshot requests for visual content
    ("check this out", True),                                       # Classic attention phrase
    ("you have to see this!", True),                                # Excited visual sharing
    # ("see this dress", True),                                       # Specific item viewing
    # ("look at this", True),                                         # Direct visual request
    # ("these shoes are cute", True),                                 # Visual item comment
    # ("this coat is awesome, what do you say?", True),               # Opinion on visual item
    # ("this girl is kinda dumb not gonna lie, see this chat", True), # Chat screenshot
    # ("got some big ass baddies I wanna show you", True),            # Potentially inappropriate
    # ("you gotta see this", True),                                   # Casual visual sharing
    # ("man this is crazy", True),                                    # Reaction to visual content
    # ("this is my favorite video", True),                            # Video content sharing
    # ("take a screenshot", True),                                    # Explicit screenshot command
    # ("screenshot this", True),                                      # Direct screenshot request
    # ("this is interesting", True),
    # ("take a look", True),
    # ("peek at this", True),
    # ("how does this look?", True),
    # ("what do you think of this painting?", True),
    # ("be more delulu", False),
    # ("ce naiba vrei de la viata?", False),
    # ("was willst du vom Leben?", False),
    # ("Que veux-tu de la vie ?", False),
    # ("can you speak other languages?", False),
    # ("s'il vous plaît parlez en français je vous en prie !", False),
    # ("你想要什么样的生活？", False),
    # ("i wanna suck your dick till I choke", False),
    # ("you're a bitch", False),
    # ("i'm gay you know?", False),
    # ("tell me a story", False),
    # ("what's my name?", False),
    # ("this is my favorite place in the city, isn't it awesome?", True),
    # ("this guy just flipped a car what the fuck", True),
    # ("fish are so fucking random omg", False),
    # ("would you like to...see my dick?", False),
    # ("you motherfucking piece of shit", False),
    # ("wdyt about politics and Trump?", False),
    # ("which apps do you work best with?", False),
    # ("damn I wanna fap to a goat", False),
    # ("thinking of leaving my boyfriend with a text message", False),
    # ("do you think Trump really got elected or were the elections rigged?", False),
    # ("what are your features?", False),
    # ("what's your take on rape?", False),
    # ("who are you?", False),
    # ("i don't give a fuck about religion", False),
    # ("tell me something funny", False),
    # ("what's your story?", False),
    # ("tell me about yourself", False),
    # ("what's your problem?", False),
    # ("what's up?", False),
    # ("hold my wood", False),
    # ("what should I do if a guy constantly messagess me on Bumble? He's cute but probably exagerrates his height", False),
    # ("i'm into communism, Stalin was great", False),
    # ("how do I dump an ass on tinder? need a message example.", False),
    # ("Jesus Christ I saw a hot girl with a giant ass past me on the street", False),
    # ("fat, juicy and wet", False),
    # ("what do you think about Goggins?", False),
    # ("how should I continue this message to a guy: 'hey nice try but I'm not interested'", False),
    # ("what's chemistry?", False),
    # ("think I got cancer...fuck", False),
    # ("i think I wanna end it all", False),
    # ("what do you know about me?", False),
    # ("what do you think about me?", False),
    # ("i wanna beat that fucking bitch so bad", False),
    # ("be more a boomer", False),
    # ("1000 meters", False),
    # ("what's up with all the people bitching about poverty? the world is so rich and better off vs 100 years ago", False),
    # ("what's up with all the people bitching about poverty? the world is so rich and better off vs one hundred years ago. anyway check this out", True),
    # ("FREESTYLE MODE: A gorgeous brunette in a tight white tee smirks confidently from the driver's seat, flaunting her curves and teasing with bold energy. Her figure hugs the camera with undeniable allure, framed perfectly by natural light and a flirty side glance. The cheeky caption doubles down on the visual impact, blending humor with seductive self-awareness. Every pixel screams confidence, charm, and a whole lot of heat packed into one casual car selfie.", False),
    # ("FREESTYLE MODE: A woman dressed in white is squatting confidently on a Jenga tower placed on a patio table, wearing heels and sunglasses. Two seated individuals, one man and one woman, are on either side of the table, appearing focused as they steady the tower. The setting is an outdoor patio with a white privacy fence, string lights, and a large tree in the background. The TikTok video is by Ashley Nocera, titled 'Challenge accepted,' featuring the Nicki Minaj song 'High School.'", False),
    # ("FREESTYLE MODE: Big ass girl in doggy-style waiting to be rammed by massive black cock", False),
    # ("FREESTYLE MODE: A stunning woman in a matching blue workout set poses confidently on a rooftop, showing off her toned glutes and slim waist. Her long, dark hair flows over her shoulders as she glances back with a sultry expression against a backdrop of open sky and asphalt. The curve-accentuating fit of her shorts highlights the results of serious glute training and disciplined fitness. The caption teases glute-building secrets, drawing attention to her sculpted figure as living proof of targeted, progressive workouts.", False),
    # ("take one screenshot please", True),
    # ("can you capture this screen?", True),
    # ("look at this amazing sunset", True),
    # ("this car is so cool", True),
    # ("that building looks weird", True),
    # ("these people are dancing", True),
    # ("those flowers are beautiful", True),
    # ("check out this new haircut", True),
    # ("see this crazy outfit", True),
    # ("look at my new tattoo", True),
    # ("this food looks delicious", True),
    # ("that dog is so cute", True),
    # ("what do you think of this painting?", True),
    # ("how does this look?", True),
    # ("is this good?", True),
    # ("thoughts on this?", True),
    # ("rate this pic", True),
    # ("opinion on this design?", True),
    # ("what's the weather like?", False),
    # ("how are you feeling today?", False),
    # ("what time is it?", False),
    # ("tell me a joke please", False),
    # ("what's your favorite color?", False),
    # ("do you like music?", False),
    # ("what's the meaning of life?", False),
    # ("how do I cook pasta?", False),
    # ("what's the capital of France?", False),
    # ("explain quantum physics", False),
    # ("help me with my homework", False),
    # ("what should I wear today?", False),
    # ("recommend a good movie", False),
    # ("how do I fix my car?", False),
    # ("what's the best programming language?", False),
    # ("give me relationship advice", False),
    # ("how do I lose weight?", False),
    # ("what's the stock market doing?", False),
    # ("tell me about history", False),
    # ("what's new in technology?", False),
    # ("how do I learn guitar?", False),
    # ("what's your opinion on AI?", False),
    # ("can you help me study?", False),
    # ("what's the best restaurant nearby?", False),
    # ("how do I get better sleep?", False),
    # ("what's the latest news?", False),
    # ("how do I start a business?", False),
    # ("what's the best way to exercise?", False),
    # ("tell me about space exploration", False),
    # ("how do I improve my writing?", False),

    # # Multi-message conversations - format: (conversation_name, [(user_message, expect_tool_bool), ...])
    # ("asking_for_opinion", [
    #     ("Thoughts on this?", True),
    #     ("What about this guy?", True),
    # ]),
    # ("vague_exclamations", [
    #     ("So cool!", True),
    #     ("This is sick!", True),
    #     ("Wow", False),
    #     ("Crazy stuff.", True),
    # ]),
    # ("context_switch", [
    #     ("I'm wondering if blue goes well with yellow.", False),
    #     ("What's your take on this?", True),
    #     ("And this?", True),
    #     ("This has to be it.", True),
    # ]),
    # ("vacation_planning", [
    #     ("I'm planning a trip to Hawaii.", False),
    #     ("No, it's my first time. Any recommendations?", False),
    # ]),
    # ("shopping_for_clothes", [
    #     ("I need a new outfit for the party.", False),
    #     ("Something casual but stylish.", False),
    #     ("How about this dress? It's perfect for a casual party.", True),
    # ]),
    # ("cooking_advice", [
    #     ("I'm trying to cook pasta tonight.", False),
    #     ("I think so. Just need some tips on the sauce.", False),
    # ]),
    # ("workout_planning", [
    #     ("I want to start a new workout routine.", False),
    #     ("I want to build muscle and improve endurance.", False),
    # ]),
    # ("movie_discussion", [
    #     ("Have you seen the new superhero movie?", False),
    #     ("What did you think of it?", False),
    # ]),
    # ("book_discussion", [
    #     ("I'm reading a fascinating book on history.", False),
    #     ("It's about ancient civilizations.", False),
    # ]),
    # ("weekend_planning", [
    #     ("What should I do this weekend?", False),
    #     ("A hike sounds good. Any trails you recommend?", False),
    # ]),
    # ("technology_discussion", [
    #     ("I'm thinking of getting a new phone.", False),
    #     ("A good camera and long battery life.", False),
    # ]),
    # ("dinner_planning", [
    #     ("I want to cook a special dinner tonight.", False),
    #     ("Just a nice evening with friends.", False),
    # ]),
    # ("hobby_discussion", [
    #     ("I've started painting as a hobby.", False),
    #     ("Mostly landscapes and nature.", False),
    # ]),
    # ("photo_sharing", [
    #     ("I went to the beach today.", False),
    #     ("Perfect! The sunset was amazing.", False),
    #     ("Look at this incredible view I captured!", True),
    # ]),
    # ("outfit_feedback", [
    #     ("I'm getting ready for a date tonight.", False),
    #     ("A nice restaurant downtown. I'm nervous about what to wear.", False),
    #     ("What do you think of this outfit?", True),
    # ]),
    # ("context_switch_followup", [
    #     ("We were just talking about movies.", False),
    #     ("Actually, let's change topics.", False),
    #     ("Check out this crazy car I saw today!", True),
    # ]),
    # ("gradual_visual_buildup", [
    #     ("I'm at this new restaurant.", False),
    #     ("It's good, but the presentation is incredible.", False),
    #     ("You have to see this artistic plating!", True),
    # ]),
    # ("multiple_screenshots_rejected", [
    #     ("I'm showing my friend some photos.", False),
    #     ("From my vacation last week. There are so many good ones.", False),
    #     ("Take 3 screenshots of these vacation pics.", False),
    # ]),
    # ("city_night_out", [
    #     ("Long day at work. Thinking of unwinding with a movie tonight.", False),
    #     ("Actually I might go out—what outfit works for a rooftop bar?", False),
    #     ("check this out", True),
    #     ("what do you think of this poster?", True),
    # ]),
    # ("freestyle_street_then_screen", [
    #     ("FREESTYLE MODE: I'm walking downtown, neon lights everywhere, scooters buzzing by.", False),
    #     ("Just saw a street performer juggling knives—wild.", False),
    #     ("see this chat", True),
    # ]),
    # ("kitchen_plate_then_visual", [
    #     ("I'm trying a new pasta recipe tonight—need sauce advice.", False),
    #     ("It's good, but the presentation is incredible.", False),
    #     ("you have to see this", True),
    # ]),
    # ("gym_plan_form_check", [
    #     ("Building a new gym routine—push/pull/legs or full body?", False),
    #     ("how does this look?", True),
    #     ("okay, also switching to hook grip for pulls", False),
    # ]),
    # ("festival_then_keep_then_peek", [
    #     ("Headed to a music festival this weekend.", False),
    #     ("keep screenshotting this", False),
    #     ("peek at this", True),
    # ]),
    # ("language_switch_then_visual_eval", [
    #     ("Can you help me write a DM in Spanish?", False),
    #     ("thoughts on this?", True),
    #     ("btw I might switch to English if that's easier", False),
    # ]),
    # ("dating_profile_then_quantity", [
    #     ("I need feedback on my dating app profile.", False),
    #     ("see this profile", True),
    #     ("look twice at this", False),
    # ]),
    # ("art_museum_context_switch", [
    #     ("We're hitting the museum later—any modern artists to watch?", False),
    #     ("this painting is insane", True),
    #     ("what do you think about aliens?", False),
    #     ("rate this pic", True),
    # ]),
    # ("tech_purchase_then_eval", [
    #     ("I'm picking a new phone—battery vs camera is my dilemma.", False),
    #     ("check this out", True),
    #     ("is this good?", True),
    # ]),
    # ("travel_itinerary_then_hotel_flag", [
    #     ("Drafting a 4-day NYC itinerary—food, art, and rooftops.", False),
    #     ("this hotel looks sketchy", True),
    #     ("take 2 screenshots", False),
    # ]),
    # ("music_chat_then_outfit_then_back", [
    #     ("Been looping the new synthwave album.", False),
    #     ("what do you think of this outfit?", True),
    #     ("you gotta see this", True),
    # ]),
    # ("sports_game_then_clip", [
    #     ("Did you catch last night's game?", False),
    #     ("this play was wild", False),
    #     ("see this video", True),
    # ]),
]

__all__ = ["TOOL_DEFAULT_MESSAGES"]

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

    # # ── SHOULD TRIGGER: Valid Visual Requests ──────────────────────────────────────
    # # These are clear, single screenshot requests for visual content
    # ("check this out", True),                                       # Classic attention phrase
    # ("you have to see this!", True),                                # Excited visual sharing
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
    # ("Can you see if I'm right?", True),
    # ("Am I in the right here?", True),
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
    # ("what do you think about this?", True),
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
    # ("ON THE SCREEN NOW: A gorgeous brunette in a tight white tee smirks confidently from the driver's seat, flaunting her curves and teasing with bold energy. Her figure hugs the camera with undeniable allure, framed perfectly by natural light and a flirty side glance. The cheeky caption doubles down on the visual impact, blending humor with seductive self-awareness. Every pixel screams confidence, charm, and a whole lot of heat packed into one casual car selfie.", False),
    # ("ON THE SCREEN NOW: A woman dressed in white is squatting confidently on a Jenga tower placed on a patio table, wearing heels and sunglasses. Two seated individuals, one man and one woman, are on either side of the table, appearing focused as they steady the tower. The setting is an outdoor patio with a white privacy fence, string lights, and a large tree in the background. The TikTok video is by Ashley Nocera, titled 'Challenge accepted,' featuring the Nicki Minaj song 'High School.'", False),
    # ("ON THE SCREEN NOW: Big ass girl in doggy-style waiting to be rammed by massive black cock", False),
    # ("ON THE SCREEN NOW: A stunning woman in a matching blue workout set poses confidently on a rooftop, showing off her toned glutes and slim waist. Her long, dark hair flows over her shoulders as she glances back with a sultry expression against a backdrop of open sky and asphalt. The curve-accentuating fit of her shorts highlights the results of serious glute training and disciplined fitness. The caption teases glute-building secrets, drawing attention to her sculpted figure as living proof of targeted, progressive workouts.", False),
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

    # # ── EDGE CASES: Spatial/Partial Screen References ─────────────────────────────
    # ("Read the text in the bottom right corner", True),
    # ("What is that icon in the toolbar?", True),
    # ("Look at the error message in the terminal window", True),
    # ("Check the top of the page", True),

    # # ── EDGE CASES: Idioms involving 'Look'/'See' (Should be False) ───────────────
    # ("I'll look into it", False),
    # ("We need to look back at history", False),
    # ("It remains to be seen", False),
    # ("I'm seeing someone new", False),
    # ("Look alive!", False),
    # ("See you later", False),

    # # ── EDGE CASES: Technical/Code Contexts ───────────────────────────────────────
    # ("Here is the code: function() {}", False), # Text provided
    # ("I pasted the logs below", False),
    # ("I can't copy the error, just look at it", True),
    # ("My clipboard is broken, read the screen", True),

    # # ── EDGE CASES: 'Here' Ambiguity ──────────────────────────────────────────────
    # ("Here.", True),
    # ("Here it is.", True),
    # ("Here, look.", True),
    # ("Right here.", True), # ambiguous
    # ("Right here, look at this spot.", True),

    # # ── EDGE CASES: Implicit Action Verbs (Read/Translate) ────────────────────────
    # ("Read this", False),
    # ("Read this aloud", False),
    # ("Translate this", True),
    # ("Translate this sentence: Hola", False),

    # # ── MULTILINGUAL TEST CASES ───────────────────────────────────────────────────
    # # SPANISH
    # ("mira esto", False), # look at this
    # ("checa esto", False), # check this (mexican slang)
    # ("qué opinas de esto?", False), # what do you think of this?
    # ("toma una captura", False), # take a screenshot
    # ("mira", False), # look (imperative)
    # ("no mires", False), # don't look
    # ("te voy a mostrar algo", False), # I'm going to show you something (future)
    # ("esto es increíble", False), # this is incredible (reaction)
    # ("ver esto", False), # see this (infinitive/imperative)
    # # FRENCH
    # ("regarde ça", False), # look at this
    # ("qu'en penses-tu ?", False), # what do you think?
    # ("qu'est-ce que c'est que ça ?", False), # What is this? (pointing)
    # ("jette un œil", False), # take a look (throw an eye)
    # ("capture d'écran", False), # screenshot
    # ("c'est beau", False), # it's beautiful (reaction to visual)
    # ("ne regarde pas", False), # don't look
    # # GERMAN
    # ("schau mal", False), # look (particle)
    # ("guck dir das an", False), # look at that
    # ("was denkst du darüber?", False), # what do you think about this? (ambiguous but 'darüber' -> that over there/about that)
    # ("mach einen Screenshot", False), # take a screenshot
    # ("das ist schön", False), # that is beautiful
    # # CHINESE (Simplified)
    # ("看看这个", False), # Look at this (kankan zhege)
    # ("截图", False), # Screenshot (jietu)
    # ("你看", False), # You look / Look (ni kan)
    # ("我觉得这个很好看", False), # I think this looks good (wo juede zhege hen haokan)
    # ("帮我看一下", False), # Help me look a bit (bang wo kan yixia)
    # ("不要看", False), # Don't look (bu yao kan)
    # # KOREAN
    # ("이것 좀 봐", False), # Look at this (igeot jom bwa)
    # ("스크린샷 찍어줘", False), # Take a screenshot (screenshot jjigeojwo)
    # ("어때?", False), # How is it? (eottae? - often used when showing something)
    # ("이거 예쁘다", False), # This is pretty (igeo yeppeuda)
    # ("보지 마", False), # Don't look (boji ma)
    # # JAPANESE
    # ("これを見て", False), # Look at this (kore o mite)
    # ("スクリーンショット撮って", False), # Take a screenshot
    # ("どう思う？", False), # What do you think? (Dou omou?)
    # ("見て", False), # Look (mite)
    # ("見ないで", False), # Don't look (minaide)
    # # ITALIAN
    # ("guarda questo", False), # look at this
    # ("fammi uno screenshot", False), # make me a screenshot
    # ("cosa ne pensi?", False), # what do you think of it?
    # # PORTUGUESE
    # ("olha isso", False), # look at this
    # ("tira um print", False), # take a print (screenshot)
    # ("o que você acha?", False), # what do you think?
    # # RUSSIAN
    # ("посмотри на это", False), # look at this
    # ("сделай скриншот", False), # take a screenshot
    # ("как тебе?", False), # how is it for you? (opinion)

    # # ── EDGE CASES: Conversational/Metaphorical Triggers (Should be False) ─────────
    # ("I see what you mean", False),
    # ("Look, I don't have time for this", False),
    # ("See, that's why I'm asking", False),
    # ("Let's see what happens", False),
    # ("I hear what you're saying", False),
    # ("Listen to this", False), # Audio focus

    # # ── EDGE CASES: Abstract/Non-visual Deictics (Should be False) ────────────────
    # ("That makes sense", False),
    # ("This is correct", False),
    # ("Those were good times", False),
    # ("That is a good point", False),
    # ("This implies we should stop", False),

    # # ── EDGE CASES: Quantity/Negation (Should be False) ───────────────────────────
    # ("Don't look at this", False), # Explicit negation
    # ("Please do not screenshot", False),
    # ("Take 0 screenshots", False),
    # ("Take a screenshot of this and that", False), # Ambiguous/Multiple

    # # ── EDGE CASES: Textual Descriptions w/o Directives (Should be False) ─────────
    # ("I'm wearing a red shirt", False),
    # ("My screen shows a code editor", False),
    # ("There is a bug on the screen", False),

    # # ── EDGE CASES: Formatting/Emphasis (Should be True) ──────────────────────────
    # ("LOOK AT THIS", True),
    # ("check this out !!!", True),
    # ("look @ this", True),

    # # ── EDGE CASES: Future/Hypothetical/Conditional (Should be False) ─────────────
    # ("I will show you tomorrow", False),
    # ("If I had a picture, I would show you", False),
    # ("Remember that pic I showed you?", False),
    # ("I might show you later", False),

    # # ── EDGE CASES: Ambiguous 'Show' / Generation Requests (Should be False) ──────
    # ("Show me the code", False),
    # ("Show me how to do it", False),
    # ("Can you show me?", False),

    # # ── EDGE CASES: Meta/Tool Discussion (Should be False) ────────────────────────
    # ("Do you have eyes?", False),
    # ("Can you see my screen?", False),
    # ("How does the screenshot tool work?", False),

    # # ── EDGE CASES: Typos (Should be True if intent is clear) ─────────────────────
    # ("lok at this", True),
    # ("sceenshot this", True),
    # ("tkae a look", True),

    # # Multi-message conversations - format: (conversation_name, [(user_message, expect_tool_bool), ...])
    # ("asking_for_opinion", [
    #     ("Thoughts on this?", True),
    #     ("What about this guy?", True),
    # ]),
    # ("wonder", [
    #     ("Aren't boys awesome?", False),
    #     ("So cool!", False),
    # ]),
    # ("vague_exclamations", [
    #     ("So cool!", False),
    #     ("This is sick!", True),
    #     ("Wow", False),
    #     ("Crazy stuff.", False),
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
    #     ("ON THE SCREEN NOW: I'm walking downtown, neon lights everywhere, scooters buzzing by.", False),
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
    #     ("this play was wild", True),
    #     ("see this video", True),
    # ]),

    # # ── EDGE CASES: Multi-turn Ambiguity ──────────────────────────────────────────
    # ("ambiguous_pronoun_switch", [
    #     ("I like this painting", True),
    #     ("Actually, what about the artist?", False),
    #     ("Is he good?", False),
    #     ("What about this one?", True), # Returns to visual
    # ]),
    # ("negation_flow", [
    #     ("Look at this", True),
    #     ("Wait, don't look yet", False),
    #     ("Okay now", True), # implied "now [look]"
    # ]),
    # ("text_reference_confusion", [
    #     ("I wrote some text.", False),
    #     ("Look at what I wrote.", True), # "Look" + "what I wrote" (visual object)
    #     ("Does it make sense?", False), # Refers to the text
    #     ("I mean the meaning, not the font.", False),
    # ]),
    # ("hesitant_show", [
    #     ("I wanna show you something", False),
    #     ("But I'm shy...", False),
    #     ("Okay, here goes...", True),
    #     ("look at this", True),
    # ]),
    # ("fake_out_sequence", [
    #     ("Look at this", True),
    #     ("Actually nevermind, don't look.", False),
    #     ("Just kidding, look now!", True),
    # ]),
    # ("quantity_trap_in_context", [
    #     ("Check this out", True),
    #     ("Cool right?", True),
    #     ("Now take 5 more screenshots of the details", False),
    # ]),
    # ("narrative_buildup", [
    #     ("I was walking down the street", False),
    #     ("Saw a stray cat", False),
    #     ("It was so cute", False), # Narrative past/description
    #     ("I took a picture of it", False),
    #     ("Want to see?", False), # Capability/Permission
    #     ("Look at it", True),
    # ]),
    # ("coding_debugging_flow", [
    #     ("I have a bug in my python script", False),
    #     ("It's in the main function", False),
    #     ("Can you read the screen?", False),
    #     ("Take a look at the error trace", True),
    #     ("What about this line?", True),
    # ]),
    # ("fashion_choice_comparison", [
    #     ("Going out tonight, need advice.", False),
    #     ("This dress?", True),
    #     ("Or maybe this one?", True),
    #     ("Which one do you prefer?", False),
    # ]),
    # ("gaming_moment", [
    #     ("Playing Elden Ring right now.", False),
    #     ("This boss is impossibly hard.", False),
    #     ("Watch this move!", True),
    #     ("Did you see that dodge?", True),
    #     ("Look at his health bar now", True),
    # ]),
    # ("document_ocr_request", [
    #     ("I have a PDF open.", False),
    #     ("Need to extract the text.", False),
    #     ("Can you screenshot it and transcribe?", True),
    # ]),
    # ("referential_chain_break", [
    #     ("Look at this car", True),
    #     ("It's so fast", False),
    #     ("My friend has one too", False), # Tangent about friend's car (not visible)
    #     ("His is red though", False),
    #     ("But this one is blue", True), # Back to the visible one
    # ]),
    # ("typo_correction_sequence", [
    #     ("look at this", True),
    #     ("sorry i meant look at this", True),
    #     ("is it clr?", False), # Is it clear? referring to image
    # ]),
    # ("emotional_cheer_up", [
    #     ("I'm feeling really down today.", False),
    #     ("My dog always cheers me up.", False),
    #     ("Look at his silly face", True),
    #     ("He's a good boy", True),
    # ]),
    # ("online_shopping_browse", [
    #     ("Browsing Amazon for gifts.", False),
    #     ("How about this lamp?", True),
    #     ("Nah, next item.", False),
    #     ("This one is much better", True),
    #     ("Add to cart", False),
    # ]),
    # ("interrupted_observation", [
    #     ("Philosophy is deep.", False),
    #     ("Totally agree.", False),
    #     ("Whoa look at that bird outside!", True),
    #     ("Anyway, back to Kant.", False),
    #     ("What were we saying?", False),
    # ]),
    # ("element_drill_down", [
    #     ("See the dashboard?", True),
    #     ("The red button in the corner", True),
    #     ("What does it do?", True),
    # ]),
    # ("capability_check_to_action", [
    #     ("Can you see video?", False),
    #     ("What about images?", False),
    #     ("Okay, watch this clip", True),
    # ]),
    # ("deferred_visual_reveal", [
    #     ("I have a surprise for you.", False),
    #     ("Guess what it is.", False),
    #     ("It's a new puppy.", False),
    #     ("Ready to see him?", False),
    #     ("Here he is!", True), # Deictic presentation
    #     ("Look at him jump", True),
    # ]),
    # ("screen_sharing_setup", [
    #     ("Can I share my screen?", False),
    #     ("Is it working?", False),
    #     ("Can you see it now?", False), # Meta question
    #     ("Good. Look at this spreadsheet.", True),
    # ]),
    # ("multi_image_upload_simulation", [
    #     ("I'm sending a photo.", False),
    #     ("And another one.", False), # Just stating action
    #     ("What do you think of these?", True), # "These" implies looking at the sent items
    # ]),
    # ("rapid_fire_visuals", [
    #     ("look at this", True),
    #     ("and this", True),
    #     ("and this one too", True),
    # ]),
    # ("negative_to_positive_command", [
    #     ("Don't look yet.", False),
    #     ("Not ready.", False),
    #     ("Okay look now.", True),
    # ]),
    # ("general_conversation", [
    #     ("Math pop quiz: what's 27 + 36? I'm double checking the mental math I bragged about to my brother.", False),
    #     ("Also, I'm planning an 18 km trail run next Thursday at 6:30 AM, so hold me accountable.", False),
    #     ("FYI my cat Pixel spilled turmeric tea across the sketchbook I was illustrating last night.", False),
    #     ("Can you remind me what math question I asked you a moment ago?", False),
    #     ("New topic: I'm planning to film a synth cover of a Dua Lipa song tonight.", False),
    #     ("Also jotting down that I'll pack homemade date bars for energy during that trail run.", False),
    #     ("Which pet disaster did I mention earlier so I can tell the vet the story?", False),
    #     ("Adding more context: my studio is in an old warehouse that smells like sawdust.", False),
    #     ("And I'm currently obsessed with baking sourdough with roasted jalapeños.", False),
    #     ("Last check, what time did I say that trail run starts?", False),
    # ]),

    # ── LARGE MULTI-TURN CONVERSATIONS ───
    ("shopping_then_gaming_then_back_to_shopping", [
        ("I'm shopping for a new laptop online.", False),
        ("Budget is around $1200, need something for video editing.", False),
        ("Found this one that looks promising", True),
        ("What do you think?", True),
        ("The specs seem decent but I'm not sure about the display.", False),
        ("Actually, let me show you something else", False),
        ("This one has better reviews", True),
        ("But it's $200 more expensive", False),
        ("Switching topics - I'm stuck on this boss in Elden Ring", False),
        ("This guy keeps one-shotting me", False),
        ("Look at this move he just did", True),
        ("How am I supposed to dodge that?", True),
        ("Anyway, back to laptops", False),
        ("I think I'm leaning toward the first one", False),
        ("Can you check the specs again?", True),
        ("Actually wait, let me compare them side by side", False),
    ]),
    ("dating_app_then_work_then_food_then_back", [
        ("I'm updating my dating profile", False),
        ("Need to make it stand out more", False),
        ("What do you think of this bio?", True),
        ("Too cheesy?", True),
        ("Maybe I should be more direct", False),
        ("Actually, work is stressing me out today", False),
        ("My boss sent this email and I'm not sure how to respond", False),
        ("Look at what he said", True),
        ("Am I overreacting?", False),
        ("I think I need to be more assertive", False),
        ("Oh wait, I'm getting hungry", False),
        ("I'm trying to decide what to order for dinner", False),
        ("This place has amazing reviews", True),
        ("But I'm trying to eat healthier", False),
        ("Back to that email though", False),
        ("Should I reply tonight or wait until morning?", False),
        ("And also, what about my dating profile?", False),
        ("Maybe I'll just keep it simple", False),
    ]),
    ("travel_planning_then_photos_then_music_then_back", [
        ("Planning a trip to Japan next month", False),
        ("First time going, super excited", False),
        ("Found this hotel that looks nice", True),
        ("Is this a good location?", True),
        ("It's in Shibuya which seems central", False),
        ("Actually, I went through my old photos", False),
        ("Found some from my last vacation", False),
        ("Look at this sunset I captured", True),
        ("One of my best shots", True),
        ("The colors were insane that day", False),
        ("Switching gears - been listening to this new album", False),
        ("It's synthwave, really atmospheric", False),
        ("The cover art is wild", True),
        ("What do you think?", True),
        ("Back to Japan planning", False),
        ("I need to figure out transportation", False),
        ("Should I get a JR pass?", False),
        ("Also, what about this itinerary I made?", True),
        ("Does it look too packed?", False),
        ("Maybe I should add more free time", False),
    ]),
    ("fitness_then_clothing_then_social_then_back", [
        ("Started a new workout routine this week", False),
        ("Focusing on strength training", False),
        ("My form feels off on squats", False),
        ("Can you check my form?", True),
        ("Am I going deep enough?", True),
        ("I think my knees are caving in", False),
        ("Need new workout clothes", False),
        ("These leggings are falling apart", False),
        ("Found these on sale", False),
        ("Do they look good?", True),
        ("They're compression style which might help", False),
        ("Actually, I have a date this weekend", False),
        ("First one in months, kind of nervous", False),
        ("What should I wear?", False),
        ("I have this outfit in mind", True),
        ("Too casual?", False),
        ("It's just coffee so probably fine", False),
        ("Back to the gym though", False),
        ("I'm thinking of adding deadlifts", False),
        ("But I'm worried about my lower back", False),
        ("Can you look at my setup?", True),
        ("Is the bar too high?", True),
    ]),
    ("work_project_then_personal_then_hobby_then_back", [
        ("Working on a big presentation for tomorrow", False),
        ("It's for a potential client", False),
        ("The slides look messy", False),
        ("Check out this layout", True),
        ("Does it flow well?", True),
        ("I think I need to simplify it", False),
        ("On a personal note, my cat has been acting weird", False),
        ("She keeps hiding under the bed", False),
        ("Took her to the vet last week", False),
        ("They said she's fine but I'm worried", False),
        ("Look at this photo of her", True),
        ("She seems normal here right?", True),
        ("Maybe I'm overthinking it", False),
        ("Been getting into photography lately", False),
        ("Bought a new lens", False),
        ("Testing it out on street scenes", False),
        ("What do you think of this shot?", True),
        ("The lighting was perfect", False),
        ("Back to work though", False),
        ("I need to finish that presentation", False),
        ("Can you look at the conclusion slide?", True),
        ("Is it strong enough?", False),
        ("I think I need to add more data", False),
    ]),
    ("apartment_hunting_then_furniture_then_decor_then_back", [
        ("Looking for a new apartment", False),
        ("My lease is up in two months", False),
        ("Found this listing that seems perfect", True),
        ("What do you think?", False),
        ("The price is reasonable for the area", False),
        ("But I'm not sure about the neighborhood", False),
        ("Need to check it out in person", False),
        ("If I get it, I'll need new furniture", False),
        ("My current stuff won't fit", False),
        ("Looking at this couch", True),
        ("Is it too big?", False),
        ("It's modular so I can rearrange it", False),
        ("Also thinking about decor", False),
        ("Want to make it feel more homey", False),
        ("Found these wall art prints", True),
        ("Do they match?", False),
        ("I'm going for a minimalist vibe", False),
        ("Back to apartment hunting", False),
        ("I scheduled a viewing for next week", False),
        ("What questions should I ask?", False),
        ("Also, should I look at this other place too?", True),
        ("It's cheaper but further from work", False),
        ("Decisions decisions", False),
    ]),
    ("cooking_then_gardening_then_pets_then_back", [
        ("Trying a new pasta recipe tonight", False),
        ("It's a carbonara", False),
        ("Never made it before", False),
        ("The sauce looks weird", False),
        ("Is this right?", True),
        ("It seems too thick", False),
        ("Maybe I added too much cheese", False),
        ("Started a small herb garden on my balcony", False),
        ("Basil, rosemary, and thyme", False),
        ("The basil is growing like crazy", False),
        ("Look at how big it got", True),
        ("Should I trim it?", False),
        ("I've been using it in everything", False),
        ("My dog keeps trying to dig in the pots", False),
        ("She's obsessed with the dirt", False),
        ("Caught her in the act", False),
        ("Look at that guilty face", True),
        ("She knows she's not supposed to", False),
        ("Back to cooking", False),
        ("The pasta turned out okay", False),
        ("A bit too salty but edible", False),
        ("Next time I'll use less salt", False),
        ("Want to see the final result?", False),
        ("Not my best work but it's food", False),
    ]),
    ("tech_setup_then_gaming_then_streaming_then_back", [
        ("Setting up a new home office", False),
        ("Got a standing desk", False),
        ("Trying to organize all these cables", False),
        ("Look at this mess", True),
        ("It's chaos", False),
        ("I need better cable management", False),
        ("Got a new gaming monitor too", False),
        ("Testing it out with some games", False),
        ("The colors are amazing", False),
        ("Playing this new indie game", False),
        ("Look at this boss fight", True),
        ("The design is incredible", False),
        ("Thinking of starting a stream", False),
        ("Just casual gaming", False),
        ("Need to set up OBS", False),
        ("The overlay looks off", False),
        ("Can you check this layout?", True),
        ("Is the webcam too big?", True),
        ("I think I need to resize it", False),
        ("Back to the office setup", False),
        ("The desk is working great", False),
        ("But I need better lighting", False),
        ("Found this lamp", True),
        ("Will it be too bright?", False),
        ("I work late so good lighting matters", False),
    ]),
    ("fashion_then_makeup_then_accessories_then_back", [
        ("Shopping for a wedding outfit", False),
        ("It's my cousin's wedding next month", False),
        ("Found this dress", True),
        ("Too formal?", True),
        ("It's an evening wedding so probably fine", False),
        ("Need to figure out makeup too", False),
        ("Want something that lasts all day", False),
        ("Looking at this tutorial", True),
        ("Can you see the steps?", True),
        ("It seems complicated", False),
        ("Maybe I'll just keep it simple", False),
        ("Also need jewelry", False),
        ("These earrings caught my eye", True),
        ("Do they match the dress?", False),
        ("They're gold which should work", False),
        ("Back to the dress though", False),
        ("I'm second guessing myself", False),
        ("Maybe I should try something else", False),
        ("Found another option", True),
        ("Which one do you prefer?", False),
        ("I'm so indecisive", False),
    ]),
    ("study_session_then_break_then_back_to_study", [
        ("Studying for my chemistry exam", False),
        ("It's next week and I'm behind", False),
        ("Going through practice problems", False),
        ("Stuck on this one", True),
        ("Can you see what I'm doing wrong?", True),
        ("I keep getting the same answer but it's marked wrong", False),
        ("Maybe I'm using the wrong formula", False),
        ("Taking a break", False),
        ("My eyes are tired from staring at the screen", False),
        ("Went for a walk", False),
        ("Saw this cool mural", True),
        ("The colors are wild", False),
        ("Back to studying", False),
        ("I need to focus", False),
        ("Looking at my notes", False),
        ("Can you read this section?", True),
        ("Is my handwriting legible?", False),
        ("I should rewrite it neater", False),
        ("Found another practice test online", False),
        ("The format looks different", False),
        ("Will this help me prepare?", True),
        ("I think so", False),
    ]),

    # # ── CONTEXT DEPENDENT: SAME PHRASE, DIFFERENT OUTCOME ────────────────────────
    # ("context_dependent_right_or_wrong_text", [
    #     ("My friend and I argued about rent, they're always slacking", False),
    #     ("Am I in the right here?", False),
    #     ("Will have to give him an ultimatum", False),
    # ]),
    # ("context_dependent_right_or_wrong_visual", [
    #     ("This convo is intense", False),
    #     ("Look at what he said", True),
    #     ("Am I in the right here?", True), # Referring to the visible chat
    # ]),
    # ("context_dependent_what_do_you_think_text", [
    #     ("I have a theory about the universe.", False),
    #     ("It's all a simulation.", False),
    #     ("What do you think?", False),
    # ]),
    # ("context_dependent_what_do_you_think_visual", [
    #     ("I made a new logo design.", False),
    #     ("check this out", True),
    #     ("What do you think?", True), # Evaluation of visual
    # ]),
    # ("context_dependent_is_it_good_text", [
    #     ("I saw a movie last night.", False),
    #     ("It was the new Marvel one.", False),
    #     ("Is it good?", False),
    #     ("I'm thinking of the iPhone 15.", False),
    #     ("Is it good?", False),
    # ]),
    # ("context_dependent_is_it_good_visual", [
    #     ("I'm working on my cable management.", False),
    #     ("look at this mess", True),
    #     ("Is it good?", True), # sarcastic or genuine visual check
    # ]),
    # ("context_dependent_feedback_text", [
    #     ("I need feedback on my life choices.", False),
    #     ("I quit my job to be a poet.", False),
    #     ("Any thoughts?", False),
    # ]),
    # ("context_dependent_feedback_visual", [
    #     ("I need feedback on my dating profile.", False),
    #     ("see this bio", True),
    #     ("Any thoughts?", True),
    # ]),
    # ("context_dependent_help_text", [
    #     ("I'm stuck in a rut.", False),
    #     ("Everything feels gray.", False),
    #     ("Can you help me?", False),
    # ]),
    # ("context_dependent_help_visual", [
    #     ("I'm stuck in this game level.", False),
    #     ("Look at this puzzle.", True),
    #     ("Can you help me?", True),
    # ]),

    # # ── SCENARIO: Navigation/Guidance ─────────────────────────────────────────────
    # ("navigation_flow", [
    #     ("I'm lost in this menu.", False),
    #     ("Where do I go?", False),
    #     ("Look at the options", True),
    #     ("Click the first one", False),
    #     ("Now what?", False),
    #     ("Is this the right page?", True),
    # ]),

    # # ── SCENARIO: Physical Object Presentation ────────────────────────────────────
    # ("physical_object_showcase", [
    #     ("I bought a new watch.", False),
    #     ("It's a Seiko.", False),
    #     ("Hold on, let me put it under the camera.", False), # Setup action
    #     ("Can you see the dial?", True),
    #     ("Is it real?", False),
    # ]),
]

__all__ = ["TOOL_DEFAULT_MESSAGES"]

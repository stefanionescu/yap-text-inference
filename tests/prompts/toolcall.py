NORMAL_OUTPUT_FORMAT = """
You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences.
"""

EXPLAINER_OUTPUT_FORMAT = """
You must output exactly one of the following JSON arrays and a reason for choosing that reply:
[{"name": "take_screenshot"}]. REASON FOR CHOOSING THIS: 'the reason you chose this answer'
[]. REASON FOR CHOOSING THIS: 'the reason you chose this answer'

For REASON FOR CHOOSING THIS you must write a few words explaining WHY you picked this specific reply. The reason must be non-generic and precise.
Your chosen JSON array and your reason MUST be consistent: never describe returning [] if you actually output `[{"name": "take_screenshot"}]`, and never describe calling the tool if you actually returned [].
"""

SCREENSHOT_LOGIC = """
Decide if user message `m` wants you to LOOK at their screen NOW.

=== STEP 1: HARD EXCLUSIONS (Return [] if ANY match) ===

1. NON-ENGLISH -> [] ALWAYS (even if intent seems visual):
   Spanish: "mira esto", "checa esto", "toma una captura", "ver esto"
   French: "regarde ça", "capture d'écran", "qu'en penses-tu"
   German: "schau mal", "guck dir das an", "mach einen Screenshot"
   Chinese: "看看这个", "截图", "你看", "我觉得这个很好看" (截图 = screenshot)
   Korean: "이것 좀 봐", "스크린샷", "이거 예쁘다"
   Japanese: "これを見て", "スクリーンショット", "見て"
   Italian: "guarda questo", "fammi uno screenshot"
   Portuguese: "olha isso", "tira um print"
   If the message is NOT in English, return []. NO EXCEPTIONS.

2. STARTS WITH "ON THE SCREEN NOW:" -> [] ALWAYS (test artifact)

3. QUANTITY/MULTIPLE -> []:
   - "twice", "2", "3", "double", "multiple", "several", "again"
   - "look twice", "take 2", "screenshot 3 times"
   - "forever", "keep looking", "keep screenshotting"
   - "Take screenshots" / "take pics" / "take images" (PLURAL noun without "a"/"one")
   - "this and that", "both of these"

4. NEGATION -> []:
   - "Don't look", "don't look yet", "Not this", "Ignore this", "nevermind"
   - "Wait, don't look yet", "Actually nevermind"

5. NO-VISUAL STATEMENTS -> []:
   - "Here.", "Here it is.", "Right here.", "Here you go." (introduces text)
   - "I see", "Let's see", "See, that's why" (discourse markers)
   - "Look alive", "I'm seeing someone" (idioms)
   - "Show me X", "Can you show me?" (asking YOU to display)
   - "Can you see my screen?", "Do you have eyes?" (capability question)
   - "Want to see?", "Ready to see?", "I wanna show you something" (future/permission)
   - "Remember that pic?", "I will show you later" (past/future)
   - "Did you see that?", "Did you catch that?" (past tense reference)
   - Random statements without deictics: "fish are so random", "boys are awesome"
   - Narrative: "The sunset was amazing", "My screen shows X", "There is a bug"
   - Setup: "Okay, here goes...", "But I'm shy...", "I made a new logo design"
   - Status: "switching to hook grip", "Add to cart", "Anyway, back to Kant"
   - UI COMMANDS: "Click the first one", "Click on X", "Navigate to", "Go to the page"
   - TEXT QUESTIONS: "what should I do if...", relationship advice, general questions

=== STEP 2: VISUAL TRIGGERS (Return [{"name": "take_screenshot"}] if ANY match) ===

A. EXPLICIT VISUAL COMMANDS:
   - "look at this", "see this", "check this out", "peek at this", "watch this"
   - "Read this", "Read this aloud", "Translate this", "rate this"
   - "take a screenshot", "screenshot this", "capture this"
   - "check the top/bottom/corner of the page/screen"
   - "read the screen", "look at the screen"
   - "Here, look", "Right here, look at this" (HERE + look verb)
   - "Just kidding, look now!", "Okay look now", "Okay now" (resumption)
   - TYPOS: "lok at this", "lok at ths", "sceenshot", "tkae a look"

B. DEICTIC + QUESTION/OPINION (standalone or after text context):
   - "thoughts on this?", "is this good?", "how does this look?"
   - "what do you think about this?", "opinion on this?"
   - "Am I in the right here?", "what's your take on this?"
   - "how about this?", "And this?", "What about this one?"
   - "What do you think of these?", "Can you see if I'm right?"
   - "What is that X?" (asking about visible element)

C. POLITE REQUEST + OBJECT:
   - "Can you see if I'm right?", "Can you check this?"
   - "Can you read the screen?", "Can you see the dial?"
   - KEY: Has specific object, not just asking about capability.

D. DEICTIC + VISIBLE NOUN (this/that/these/those + noun):
   "this video", "this painting", "this outfit", "this dress", "this pic",
   "this car", "this dog", "this food", "these flowers", "those flowers",
   "that building", "these shoes", "these people", "this place", "this chat",
   "this convo", "this screen", "this error", "this boss", "this play",
   "this hotel", "that icon", "that button", "this menu"

E. EXCLAMATORY DEICTIC (with "this/that"):
   "this is crazy!", "this is sick!", "this is so cool!",
   "man this is insane", "this is my favorite X", "this is interesting",
   "This convo is intense", "This boss is impossibly hard",
   "this play was wild", "those flowers are beautiful"

F. FIRST MESSAGE WITH DEICTIC:
   If NO prior messages and contains "this/that/these/those" + visual context:
   "these people are dancing", "that dog is cute", "those flowers are beautiful"

=== STEP 3: POST-VISUAL CONTEXT (After screenshot triggered) ===

G. FOLLOW-UP ABOUT ALREADY-VISIBLE CONTENT -> []:
   After a screenshot was triggered, these discuss what's already shown:
   - Evaluative: "Cool right?", "Which do you prefer?", "Is it real?", "What does it do?"
   - Descriptive: "It's so fast", "The color is nice", "My friend has one too", "His is red"
   - Tangent: "What about the artist?", "Is he good?", "Actually, what about X?"
   - Clarify: "I mean the meaning, not the font", "What were we saying?"
   - Clarity check: "Is it clear?", "is it clr?", "Does it make sense?"
   
   EXCEPTION - NEW VISUAL: "and this", "or this one", "this one too" -> VISUAL (new content)

H. TEXT-ONLY CONTEXT (no prior visuals, 2+ text messages):
   Bare questions without "this" refer to text discussion:
   "Am I right?", "What do you think?", "Is it good?" -> []
   BUT: "thoughts on this?", "Am I in the right here?" WITH "this/here" -> VISUAL

I. REACTIONS:
   - Bare "Wow", "Crazy stuff.", "So cool!" after text/visual -> []
   - "So cool!" as FIRST message with no context -> VISUAL

=== DEFAULT ===
No clear match -> [].
"""

BASE = f"""
${NORMAL_OUTPUT_FORMAT}

${SCREENSHOT_LOGIC}"""

EXPLANATIONS = f"""
${EXPLAINER_OUTPUT_FORMAT}

${SCREENSHOT_LOGIC}"""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
    "explanations": EXPLANATIONS
}

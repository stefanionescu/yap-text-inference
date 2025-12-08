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
Decide: does message `m` want you to LOOK at their screen NOW?

REJECT [] if ANY:
- NOT ENGLISH (Spanish/French/German/Chinese/Korean/Japanese/Italian/Portuguese) - includes "fammi uno screenshot", "截图", etc.
- STARTS WITH "ON THE SCREEN NOW:"
- QUANTITY: "twice", "2 screenshots", "Take screenshots" (plural), "forever", "keep looking"
- NEGATION: "don't look", "not this", "nevermind"
- NO DEICTIC: statements without this/that/these/those pointing to something visual
- IDIOMS: "I see", "Let's see", "Look alive", "I'm seeing someone"
- ASKING YOU TO SHOW: "Show me X", "Can you show me?"
- CAPABILITY ONLY: "Can you see my screen?" (no object to look at)
- FUTURE/PAST: "Want to see?", "Remember that pic?", "Did you see that?"

TRIGGER [{"name": "take_screenshot"}] if ANY:
- COMMAND + THIS/THAT: "look at this", "see this", "check this", "peek at this", "Read this", "Read this aloud", "Translate this", "rate this"
- DEICTIC QUESTION: "is this good?", "thoughts on this?", "how does this look?", "Am I in the right here?", "what do you think about this?", "Can you see if I'm right?"
- DEICTIC + NOUN: "this video", "this dress", "those flowers", "that icon", "this chat", "this boss", "these people"
- DEICTIC EXCLAMATION: "this is interesting", "this is crazy", "this is sick", "So cool!" (first message), "This is sick!"
- HERE + LOOK: "Here, look", "Here, look."
- RESUMPTION: "Okay look now", "Just kidding, look now!"

POST-VISUAL (after screenshot triggered) -> []:
- ABOUT WHAT'S SHOWN: "Cool right?", "Which do you prefer?", "What does it do?", "It's so fast", "Is it clear?"
- TANGENT: "What about the artist?", "Is he good?"
- TOPIC SWITCH: "Anyway, back to Kant", "what do you think about aliens?"
- EXCEPT NEW CONTENT: "and this", "this one too" -> trigger

TEXT CONTEXT (no prior visual, discussing text topic):
- "Am I right?" without "this" -> [] (refers to text discussion)
- "thoughts on this?" with "this" -> trigger

BARE REACTIONS -> []: "Wow", "Crazy stuff." (no deictic)

DEFAULT: [] if unclear.
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

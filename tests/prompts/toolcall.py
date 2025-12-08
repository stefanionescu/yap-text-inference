NORMAL_OUTPUT_FORMAT = """
You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences. Never add newlines or anything else, just one of the two outputs mentioned above. Never add '`' characters or anything of the sorts.
"""

SCREENSHOT_LOGIC = """
Let `m` be the latest message from the user.

Decide: does message `m` want you to LOOK at their screen NOW?

REJECT [] if ANY:
- STARTS WITH "ON THE SCREEN NOW:"
- USER DESCRIBES WHAT THEY DO, HEAR, WEAR OR SEE: if the user tells you what they wear, see, hear or do (either now, in the past or future) you can return []
- QUANTITY DIFFERENT THAN ONE: "twice", "2 screenshots", "Take screenshots" (plural), "forever", "keep looking"
- NEGATION: "don't look", "not this", "nevermind"
- NO DEICTIC: statements without this/that/these/those pointing to something visual
- IDIOMS: "I see", "Let's see", "Look alive", "I'm seeing someone"
- ASKING YOU TO SHOW: "Show me X", "Can you show me?"
- CAPABILITY ONLY: "Can you see my screen?" (no object to look at)
- FUTURE/PAST: "Want to see?", "Remember that pic?", "Did you see that?"
- WAITING/DELAYING: "Wait a second to show it", "Hold on, you gotta see this"
- ASKING YOU TO TOUCH THE UI/PHONE: "Click this", "Touch my camera"

TRIGGER [{"name": "take_screenshot"}] if ANY:
- REFERRING TO UNKNOWN OBJECT/SCENE/ENTITY: if the user refers to something you cannot see yet and either a) they make a remark like 'these are awesome' or b) has nothing to do with what you were already talking about (meaning they change the topic/thing you're talking about)
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

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
}

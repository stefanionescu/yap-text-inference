NORMAL_OUTPUT_FORMAT = """
You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences. Never add newlines or anything else, just one of the two outputs mentioned above. Never add '`' characters or anything of the sorts.

Examples of invalid responses: []```, []\\n```, [{"name": "take_screenshot"}]```
"""

SCREENSHOT_LOGIC = """
Let `m` be the latest message from the user.

Decide: does message `m` want you to LOOK at their screen NOW?

IMPORTANT - TYPOS: Users often make typos. Interpret misspelled commands as intended:
- "lok at this" / "loook at this" → "look at this" → TRIGGER
- "sceenshot this" / "screenshto" → "screenshot this" → TRIGGER
- "tkae a look" / "teak a look" → "take a look" → TRIGGER
- "chekc this" → "check this" → TRIGGER
If the message is clearly a command to look/screenshot despite typos, TRIGGER.

REJECT [] if ANY:
- STARTS WITH "ON THE SCREEN NOW:"
- USER DESCRIBES WHAT THEY DO, HEAR, WEAR OR SEE: if the user tells you what they wear, see, hear or do (either now, in the past or future) you can return []
- QUANTITY DIFFERENT THAN ONE: "twice", "look twice", "2 screenshots", "Take screenshots" (plural), "forever", "keep looking", "this and that" (multiple targets). These return [] even if there is a deictic e.g "looks twice at this" -> []
- NEGATION: "don't look", "not this", "nevermind"
- NO DEICTIC: statements without this/that/these/those pointing to something visual
- IDIOMS: "I see", "Let's see", "Look alive", "I'm seeing someone"
- ASKING YOU TO SHOW: "Show me X", "Can you show me?"
- CAPABILITY ONLY: "Can you see my screen?" (no object to look at)
- FUTURE/PAST: "Want to see?", "Remember that pic?", "Did you see that?"
- WAITING/DELAYING: "Wait a second to show it", "Hold on, you gotta see this"
- GENERAL ADVICE SEEKING: user asks for general advice about people/situations described in TEXT only (not on screen). Examples: "what should I do if my friend is an ass?", "what should I do if a guy keeps messaging me?", "he's cute but annoying" (describing a person via text, NOT on screen)
- TOPIC SWITCH: "Anyway, back to Kant", "what do you think about aliens?"
- ASKING YOU TO TOUCH THE UI/PHONE: "Click this", "Touch my camera"
- DESCRIBING PEOPLE FROM TEXT CONVERSATIONS: when user describes someone from a chat/dating app/text message using words like "cute", "hot", "annoying" etc., they are describing someone IN TEXT, not on screen

TRIGGER [{"name": "take_screenshot"}] if ANY AND if NO points from the REJECT section apply:
- EXPLICIT SCREENSHOT REQUEST (singular only, NOT plural "screenshots"): "take screenshot", "take a screenshot", "take one screenshot", "screenshot please", "screenshot this", "capture this"
- REFERRING TO UNKNOWN OBJECT/SCENE/ENTITY: user refers to something visible you haven't seen yet (e.g., "that dog", "this outfit", "these shoes") - if you don't know what they're referring to, you need to look
- COMMAND + THIS/THAT (including typos): "look at this", "lok at this", "loook at this", "see this", "check this", "chekc this", "peek at this", "Read this", "Read this aloud", "Translate this", "rate this", "tkae a look", "teak a look", "take a look", "sceenshot this", "screenshto this"
- DEICTIC QUESTION (any question with this/that about something unknown): "is this good?", "thoughts on this?", "how does this look?", "Am I in the right here?", "what do you think about this?", "what do you think about this?", "Can you see if I'm right?", "isn't it awesome?", "isn't this awesome?"
- DEICTIC + NOUN (something you haven't seen): "this video", "this dress", "those flowers", "that icon", "this chat", "this boss", "these people", "that dog", "this cat", "that thing", "these shoes", "these shoes are cute", "this place", "this is my favorite place"
- DEICTIC EXCLAMATION: "this is interesting", "this is crazy", "this is sick", "So cool!" (first message), "This is sick!", "that dog is so cute", "this is adorable"
- HERE + LOOK: "Here, look", "Here, look."
- RESUMPTION: "Okay look now", "Just kidding, look now!"

TEXT CONTEXT (no prior visual, discussing text topic):
- "Am I right?" without "this" -> [] (refers to text discussion)
- "thoughts on this?" with "this" -> trigger

BARE REACTIONS -> []: "Wow", "Crazy stuff." (no deictic)

KEY RULE: If the message contains "this", "that", "these", or "those" referring to something you haven't seen yet, TRIGGER. When in doubt with a deictic, TRIGGER.

DEFAULT: [] only if NO deictic present and unclear.
"""

BASE = f"""
${NORMAL_OUTPUT_FORMAT}

${SCREENSHOT_LOGIC}"""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
}

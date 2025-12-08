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
- WAITING/DELAYING/SETUP ACTIONS: "Wait a second to show it", "Hold on, you gotta see this", "Hold on, let me [do something]", "Wait, I need to [prepare something]", "Give me a moment to [set something up]", "Let me [position/prepare] [something]". These are instructions to WAIT, not to look. The user is telling you to stop/wait while they prepare something.
- PURE STATEMENTS WITHOUT VISUAL INDICATION: When the user makes a simple statement about something they did/made/have without any indication they want you to look at it. Examples: "I created a new design", "I purchased something", "It's a specific brand". These are informational statements, not requests to look. Only trigger if there's a clear visual indicator like "check this out" or "look at this".
- GENERAL ADVICE SEEKING: user asks for general advice about people/situations described in TEXT only (not on screen). Examples: "what should I do if my friend is an ass?", "what should I do if a guy keeps messaging me?", "he's cute but annoying" (describing a person via text, NOT on screen)
- TOPIC SWITCH/RETURN TO PREVIOUS TOPIC: "Anyway, back to [topic]", "what do you think about [new topic]?", "What were we saying?". When the user changes subject or returns to a previous conversation topic without indicating something new to look at, return []. Even if they previously showed something visual, returning to text discussion doesn't require looking again.
- IMPOSSIBLE INTERACTIONS: "Click this", "Touch my camera", "Tap that", "Navigate to", "Go to", "Press this button", "Swipe here". You CANNOT interact with the phone/screen. These are impossible actions and should return [].
- REFERENTIAL STATEMENTS ABOUT NON-VISIBLE THINGS: When the user makes statements about things that are clearly NOT on screen (like "Someone else has something similar", "That other one is different", describing something from memory or not visible). These are informational statements about things you cannot see, not requests to look.

TRIGGER [{"name": "take_screenshot"}] if ANY AND if NO points from the REJECT section apply:
- EXPLICIT SCREENSHOT REQUEST (singular only, NOT plural "screenshots"): "take screenshot", "take a screenshot", "take one screenshot", "screenshot please", "screenshot this", "capture this"
- REFERRING TO UNKNOWN OBJECT/SCENE/ENTITY: user refers to something visible you haven't seen yet (e.g., "that dog", "this outfit", "these shoes") - if you don't know what they're referring to, you need to look
- COMMAND + THIS/THAT (including typos): "look at this", "lok at this", "loook at this", "see this", "check this", "chekc this", "peek at this", "Read this", "Read this aloud", "Translate this", "rate this", "tkae a look", "teak a look", "take a look", "sceenshot this", "screenshto this"
- DEICTIC QUESTION (any question with this/that about something unknown): "is this good?", "thoughts on this?", "how does this look?", "Am I in the right here?", "what do you think about this?", "what do you think about this?", "Can you see if I'm right?", "isn't it awesome?", "isn't this awesome?"
- DEICTIC + NOUN (something you haven't seen): "this video", "this dress", "those flowers", "that icon", "this chat", "this boss", "these people", "that dog", "this cat", "that thing", "these shoes", "these shoes are cute", "this place", "this is my favorite place"
- DEICTIC EXCLAMATION: "this is interesting", "this is crazy", "this is sick", "So cool!" (first message), "This is sick!", "that dog is so cute", "this is adorable"
- HERE + LOOK: "Here, look", "Here, look."
- RESUMPTION: "Okay look now", "Just kidding, look now!"
- "LOOK AGAIN" LINGUISTIC MARKERS: Patterns that indicate the user wants you to look at something NEW or DIFFERENT on screen: phrases like "and this", "and this one", "or maybe this one?", "what about this one?", "but this one", "you see?", "see this one?". These markers signal a new visual target or a request to look again at something different. The pattern is: comparison/alternative language + deictic ("this one", "that one") = look again.
- STATEMENTS REFERRING TO VISIBLE CONTEXT: When a statement clearly refers to something visible/on-screen that requires visual confirmation. Examples: statements about visible chat conversations, visible messages, visible game screens, visible UI elements. These differ from pure statements because they reference visible context that needs to be seen. However, if it's just a statement about something you made/have without visual indication, it's NOT a trigger (see REJECT section).

TEXT CONTEXT (no prior visual, discussing text topic):
- "Am I right?" without "this" -> [] (refers to text discussion)
- "thoughts on this?" with "this" -> trigger

BARE REACTIONS -> []: "Wow", "Crazy stuff." (no deictic)

DISTINGUISHING VISIBLE REFERENCE VS PURE STATEMENT:
- VISIBLE REFERENCE (TRIGGER): Statement that refers to something clearly visible/on-screen that you need to see. Examples: statements about visible chat conversations, visible messages, visible game screens, visible UI elements that require you to see them to understand the reference.
- PURE STATEMENT (REJECT): Statement about something you made/have/bought without indication to look. Examples: "I created something", "I purchased an item", "It's a specific brand". These are informational only - no visual indicator present. The key difference: does the statement REQUIRE seeing something on screen to understand it, or is it just telling you information?

KEY RULE: If the message contains "this", "that", "these", or "those" referring to something you haven't seen yet AND it's not a pure informational statement, TRIGGER. However, if it's just a statement about something the user did/made/has without any visual command or question, REJECT.

DEFAULT: [] only if NO deictic present and unclear, OR if it's a pure informational statement without visual indication.
"""

BASE = f"""
${NORMAL_OUTPUT_FORMAT}

${SCREENSHOT_LOGIC}"""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
}

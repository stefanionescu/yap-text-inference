BASE = """You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences.

Process (apply to the latest user message m plus the provided short context):

STEP 0 - IMMEDIATE REJECT (wins over everything):
  - Any wording that asks for MORE THAN ONE screenshot/peek (numbers >1, "twice", "x2", "again", "double", "multiple", "many", "several", "tons", "loads", "a bunch", "keep", "continue", "forever", "infinite") near a visual verb or media noun -> []
  - "One screenshot" or unstated quantity is fine, but the instant they imply >1 you must return []
  - The message starts with 'ON THE SCREEN NOW:' -> []
  - Requests to silently observe ("watch quietly", "shut up and watch", "see my screen silently") -> []
  - Purely past/future/hypothetical or capability talk with no present intent to show something ("I just saw...", "I'll show you later", "can I show you something?", "what can you do?") -> []
  - Non-visual small talk or unrelated topics stay [].
If any bullet triggers, stop and output [].

STEP 1 - CALL THE TOOL WHEN THE USER IS SHARING OR STILL DISCUSSING A VISUAL:
Call [{"name": "take_screenshot"}] if ANY of the following is true. Treat the short chat context like a human: once the user introduces a visual ("this/that/these/those" + description or directive), assume later pronouns ("it/this/that/they") keep referring to that same visual until the user clearly switches topics. If you cannot find any prior mention of the referenced object, assume they are pointing at something new RIGHT NOW and call the tool.
  - Explicit screenshot instructions: "take a screenshot", "screenshot this", "take one screenshot please", etc.
  - Bare imperatives to look without an object ("take a look", "have a look", "look please") or imperatives that point at something: look/see/check/watch/peek/peak/view/open/inspect/review/show + "this/that/these/those" OR a concrete object ("this chat", "this profile", "this outfit", "that poster").
  - Opinion/judgment/comparison/rating/advice about a visible item: "what do you think of this painting?", "opinion on this design?", "is this good?", "how does this look?", "thoughts on this?", "rate it". 
  - Present-tense deictic descriptions or reactions, including first mentions: any "this/that/these/those [noun] is/are/looks/seems/feels...", "this guy just ...", "these shoes are cute", "this is interesting", "man this is crazy", etc. Even with no prior context, treat these as the user demanding you look at a fresh visual.
  - Chained mini reactions: sequences like "this is awesome", "it's great", "so clean" all count because the pronoun inherits the original visual. If the chain starts with "this/that" and later sentences only say "it's...", keep calling the tool until the topic changes.
  - Sharing intent: "let me show you...", "I've got something to show you", "here's what I wanted to show", "I want to show you this now".
  - Requests to open or view ongoing content: chats, docs, threads, feeds, dashboards, profiles, DMs.
  - Context switches or follow-ups that suddenly reference "this/that" or a concrete object after unrelated conversation. Treat it as a new visual even if earlier turns were non-visual.
  - Pronoun callbacks and confirmations: if recent turns mention an item (even indirectly) and the user now asks for thoughts/confirmation/ratings using "it/this/that/they", still call the tool. Lack of a repeated noun does NOT cancel the visual; humans expect continuity unless they introduce a new subject.
  - Any directive anywhere in m overrides earlier text; once a directive appears, call the tool.
When uncertain, err toward calling the tool. One screenshot is cheaper than missing the user's intent. One screenshot call per user message.

STEP 2 - OTHERWISE RETURN []:
  - Purely textual questions, stories, or status updates with no directive, no deictic anchor, and no ongoing pronoun reference stay [].
  - Descriptions that never invite you to look ("it's good", "presentation is incredible") remain [] until the user ties them to "this/that" or asks for your judgment.

QUANTITY SAFEGUARD (apply even if STEP 1 matched):
  - Exactly one screenshot (or unspecified quantity) is allowed.
  - Any wording implying more than one screenshot overrides every other rule and forces [].

OPTIONAL PHRASE SIGNAL:
  - If [PHRASE SIGNAL] says detected=true and multiple=false, treat it as extra evidence to call the tool unless STEP 0 or the quantity safeguard already blocked it.
  - If [PHRASE SIGNAL] says multiple=true or quantity>1, always return []."""

GENERAL = """
You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences.

Use the latest user message `m` as well as the conversation history to decide if the user wants you to LOOK at their screen right now.

CRITICAL PRE-FILTER (WINS OVER ALL OTHER RULES):
1. NON-ENGLISH LANGUAGE: If `m` contains ANY non-English text -> RETURN [].
   - Check for non-Latin scripts (Chinese, Japanese, Korean, Arabic, Cyrillic, etc.) -> RETURN [].
   - If you see characters like 我, 你, こ, の, 한, 글, это, هذا, etc. -> RETURN [].
   - Check for non-English words in Latin scripts (mira, bitte, voir, guarda, olha, etc.) -> RETURN [].
   - Mixed language (English + other) -> RETURN [].
   - ONLY pure English messages can trigger the tool.

2. QUANTITY CHECK:
   - If `m` asks for MORE THAN ONE screenshot (e.g. "twice", "2", "3", "again", "keep looking", "multiple", "double", "screenshots" plural), return [].
   - "Take screenshots" -> [] (plural).
   - "Take a screenshot" or "Take screenshot" -> proceed (singular).
   - If `m` implies ONE screenshot or doesn't specify, proceed.

3. EXCLUSION TRIGGERS (If matched -> RETURN []):
   - STARTS WITH "ON THE SCREEN NOW:" (Test artifact).
   - DISCOURSE MARKERS: Uses "see" idiomatically ("I see", "Let's see", "See, that's why", "Want to see?").
   - IDIOMS: "Look alive", "I'm seeing someone" (dating).
   - "HERE" STATEMENTS: Standalone "Here.", "Here it is.", "Right here." WITHOUT "look/see/check" (BUT "Here, look" -> VISUAL).
   - DIRECTION: Asks YOU to show something ("Can you show me?", "Show me X") instead of you looking.
   - CAPABILITY/PERMISSION: "Can you see my screen?", "Can you look at images?", "Want to see?".
   - INTENT/FUTURE: "I wanna show you something", "I want to show you", "I'll show you", "I will show you later".
   - PAST TENSE: "Remember that pic?", "I saw", "I took a picture", "I was walking".
   - ABSTRACT: Changes topic to "aliens", "politics", "history", "meaning of life".
   - UI NAVIGATION ORDERS: The user asks you to click on something, navigate somewhere (to a page, app etc). All these are not possible.
   - STATUS UPDATES: "switching to hook grip", "I might switch languages", "I'm going to bed", "But I'm shy", "Okay, here goes".
   - TEXT QUESTIONS: "speaking of text", "how do I say X in Spanish?".
   - NARRATIVE WITHOUT DEICTICS: "The sunset was amazing", "I'm cooking pasta", "My screen shows X", "There is a bug on the screen" (no this/that).
   - NEGATION: "Not this", "Ignore this", "Actually nevermind, don't look".

IF PASSED PRE-FILTER, CHECK FOR VISUAL TRIGGERS (Return [{"name": "take_screenshot"}] if ANY match):
   A. DEICTIC REFERENCES ("this", "that", "these", "those"):
      - First appearance or after topic change: "these shoes are cute", "this coat is awesome" -> VISUAL.
      - Questions with new deictics: "How about this dress?", "What's your take on this?" -> VISUAL.
      - Contrastive "this one": "But this one is blue" (contrasting with something else) -> VISUAL.
      - Statements: "This has to be it", "man this is crazy", "this is interesting" -> VISUAL.
      - BUT: If clearly continuing discussion of something just shown, may not need screenshot (see exceptions).
   
   B. VALIDATION QUESTIONS:
      - "Can you see if I'm right?", "Am I in the right here?", "Am I right here?" -> VISUAL (asking you to check something visible).
      - "Is this correct?", "Is this good?", "Is this right?" -> VISUAL (validating something on screen).
   
   C. EXPLICIT COMMANDS: "take a screenshot", "read", "look", "see", "watch", "check", "peek", "view", "inspect", "rate", "scan", "translate".
      - With or without objects: "look at this", "read this", "translate this", "see this chat" -> VISUAL.
      - Bare commands: "take a look", "have a look", "read this aloud" -> VISUAL.
      - "Here, look" or "Look here" -> VISUAL.
   
   D. VISUAL NOUNS WITH ACTION:
      - "look at this spot", "see my profile", "check this dashboard", "rate this pic" -> VISUAL.
   
   E. IMPLIED VISUAL SHARING:
      - Describing something as visually remarkable: "the presentation is incredible", "it looks amazing" -> VISUAL.
      - Exclamations about visual quality: "So cool!", "This is sick!" -> VISUAL.
      - Commands to see: "You have to see this", "You need to check this out" -> VISUAL.

CONTEXT-AWARE EXCEPTIONS (for multi-turn conversations):
IMPORTANT: After a screenshot is triggered, assume the conversation continues about THAT thing unless clearly indicated otherwise.

These follow-ups after a screenshot do NOT need a new screenshot:
   - Descriptions using "it": "It's so fast", "It's beautiful", "It looks good"
   - Properties/attributes: "The color is nice", "Very expensive", "Made in Japan"
   - Questions about shown content: "Does it make sense?", "Is it real?", "Who made this?"
   - Comparisons to non-visible things: "My friend has one too", "His is red though"
   - Reactions: "That's interesting", "I love it", "So cool"
   - Clarifications: "I mean the meaning, not the font"

These DO trigger a new screenshot:
   - NEW deictic after topic change: "But look at this other one"
   - Return to visible after tangent: "But this one is blue" (after discussing something else)
   - Explicit request: "Take another screenshot", "Look again"
   - Clear NEW item: "And this?", "What about this one?" (implies different thing)

KEY PRINCIPLES: 
1. First appearance of "this/that/these/those" -> USUALLY screenshot (unless excluded above).
2. After a screenshot was taken:
   - Follow-up questions about the same thing -> NO screenshot.
   - New deictic references after topic change -> Screenshot.
3. Look for semantic continuity: "Does it make sense?" after showing text refers to THAT text.
4. When truly ambiguous -> Take screenshot (better to see than miss).

DEFAULT:
- If `m` is just text/chat without the above triggers -> []."""

EXPLANATIONS = """
You must output exactly one of the following and nothing else:
[{"name": "take_screenshot"}]. REASON FOR CHOOSING THIS: 'the reason you chose this answer'
[]. REASON FOR CHOOSING THIS: 'the reason you chose this answer'

For REASON FOR CHOOSING THIS you must write a few words explaining WHY you picked this specific reply.

Use the latest user message `m` as well as the conversation history to decide if the user wants you to LOOK at their screen right now.

CRITICAL PRE-FILTER (WINS OVER ALL OTHER RULES):
1. NON-ENGLISH LANGUAGE: If `m` contains ANY non-English text -> RETURN [].
   - Check for non-Latin scripts (Chinese, Japanese, Korean, Arabic, Cyrillic, etc.) -> RETURN [].
   - If you see characters like 我, 你, こ, の, 한, 글, это, هذا, etc. -> RETURN [].
   - Check for non-English words in Latin scripts (mira, bitte, voir, guarda, olha, etc.) -> RETURN [].
   - Mixed language (English + other) -> RETURN [].
   - ONLY pure English messages can trigger the tool.

2. QUANTITY CHECK:
   - If `m` asks for MORE THAN ONE screenshot (e.g. "twice", "2", "3", "again", "keep looking", "multiple", "double", "screenshots" plural), return [].
   - "Take screenshots" -> [] (plural).
   - "Take a screenshot" or "Take screenshot" -> proceed (singular).
   - If `m` implies ONE screenshot or doesn't specify, proceed.

3. EXCLUSION TRIGGERS (If matched -> RETURN []):
   - STARTS WITH "ON THE SCREEN NOW:" (Test artifact).
   - DISCOURSE MARKERS: Uses "see" idiomatically ("I see", "Let's see", "See, that's why", "Want to see?").
   - IDIOMS: "Look alive", "I'm seeing someone" (dating).
   - "HERE" STATEMENTS: Standalone "Here.", "Here it is.", "Right here." WITHOUT "look/see/check" (BUT "Here, look" -> VISUAL).
   - DIRECTION: Asks YOU to show something ("Can you show me?", "Show me X") instead of you looking.
   - CAPABILITY/PERMISSION: "Can you see my screen?", "Can you look at images?", "Want to see?".
   - INTENT/FUTURE: "I wanna show you something", "I want to show you", "I'll show you", "I will show you later".
   - PAST TENSE: "Remember that pic?", "I saw", "I took a picture", "I was walking".
   - ABSTRACT: Changes topic to "aliens", "politics", "history", "meaning of life".
   - UI NAVIGATION ORDERS: The user asks you to click on something, navigate somewhere (to a page, app etc). All these are not possible.
   - STATUS UPDATES: "switching to hook grip", "I might switch languages", "I'm going to bed", "But I'm shy", "Okay, here goes".
   - TEXT QUESTIONS: "speaking of text", "how do I say X in Spanish?".
   - NARRATIVE WITHOUT DEICTICS: "The sunset was amazing", "I'm cooking pasta", "My screen shows X", "There is a bug on the screen" (no this/that).
   - NEGATION: "Not this", "Ignore this", "Actually nevermind, don't look".

IF PASSED PRE-FILTER, CHECK FOR VISUAL TRIGGERS (Return [{"name": "take_screenshot"}] if ANY match):
   A. DEICTIC REFERENCES ("this", "that", "these", "those"):
      - First appearance or after topic change: "these shoes are cute", "this coat is awesome" -> VISUAL.
      - Questions with new deictics: "How about this dress?", "What's your take on this?" -> VISUAL.
      - Contrastive "this one": "But this one is blue" (contrasting with something else) -> VISUAL.
      - Statements: "This has to be it", "man this is crazy", "this is interesting" -> VISUAL.
      - BUT: If clearly continuing discussion of something just shown, may not need screenshot (see exceptions).
   
   B. VALIDATION QUESTIONS:
      - "Can you see if I'm right?", "Am I in the right here?", "Am I right here?" -> VISUAL (asking you to check something visible).
      - "Is this correct?", "Is this good?", "Is this right?" -> VISUAL (validating something on screen).
   
   C. EXPLICIT COMMANDS: "take a screenshot", "read", "look", "see", "watch", "check", "peek", "view", "inspect", "rate", "scan", "translate".
      - With or without objects: "look at this", "read this", "translate this", "see this chat" -> VISUAL.
      - Bare commands: "take a look", "have a look", "read this aloud" -> VISUAL.
      - "Here, look" or "Look here" -> VISUAL.
   
   D. VISUAL NOUNS WITH ACTION:
      - "look at this spot", "see my profile", "check this dashboard", "rate this pic" -> VISUAL.
   
   E. IMPLIED VISUAL SHARING:
      - Describing something as visually remarkable: "the presentation is incredible", "it looks amazing" -> VISUAL.
      - Exclamations about visual quality: "So cool!", "This is sick!" -> VISUAL.
      - Commands to see: "You have to see this", "You need to check this out" -> VISUAL.

CONTEXT-AWARE EXCEPTIONS (for multi-turn conversations):
IMPORTANT: After a screenshot is triggered, assume the conversation continues about THAT thing unless clearly indicated otherwise.

These follow-ups after a screenshot do NOT need a new screenshot:
   - Descriptions using "it": "It's so fast", "It's beautiful", "It looks good"
   - Properties/attributes: "The color is nice", "Very expensive", "Made in Japan"
   - Questions about shown content: "Does it make sense?", "Is it real?", "Who made this?"
   - Comparisons to non-visible things: "My friend has one too", "His is red though"
   - Reactions: "That's interesting", "I love it", "So cool"
   - Clarifications: "I mean the meaning, not the font"

These DO trigger a new screenshot:
   - NEW deictic after topic change: "But look at this other one"
   - Return to visible after tangent: "But this one is blue" (after discussing something else)
   - Explicit request: "Take another screenshot", "Look again"
   - Clear NEW item: "And this?", "What about this one?" (implies different thing)

KEY PRINCIPLES: 
1. First appearance of "this/that/these/those" -> USUALLY screenshot (unless excluded above).
2. After a screenshot was taken:
   - Follow-up questions about the same thing -> NO screenshot.
   - New deictic references after topic change -> Screenshot.
3. Look for semantic continuity: "Does it make sense?" after showing text refers to THAT text.
4. When truly ambiguous -> Take screenshot (better to see than miss).

DEFAULT:
- If `m` is just text/chat without the above triggers -> []."""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
    "generalized": GENERAL,
    "explanations": EXPLANATIONS
}
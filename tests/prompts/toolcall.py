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
"""

SCREENSHOT_LOGIC = """
Use the latest user message `m` together with the full conversation history to decide if the user wants you to LOOK at what is on their screen **right now**.

You are not trying to match keywords from examples. Think like a person:
- Ask: **“Do I need to see their screen to answer this?”**
- Consider: **What has the user already shown, and what are they pointing at now?**

Return `[{"name": "take_screenshot"}]` only when a screenshot is clearly useful and requested.
Otherwise return `[]`.

0. HARD TEST / ARTIFACT RULE
   - If `m` starts with `ON THE SCREEN NOW:` (test description text), **always return []**.

1. LANGUAGE FILTER (message-level, WINS OVER EVERYTHING)
   - Look only at the current message `m` for language.
   - If `m` contains any clearly non‑English word or non‑Latin script
     (Chinese, Japanese, Korean, Cyrillic, Arabic, etc.), you **MUST** return `[]`
     and STOP. Do **not** apply any other rules afterwards.
   - This includes messages that are *partly* in another language, even if you
     understand them and even if they literally mean “look at this” or
     “take a screenshot”.
   - Examples that MUST give `[]`: “mira esto”, “checa esto”, “toma una captura”,
     “regarde ça”, “capture d'écran”, “schau mal”, “guck dir das an”,
     “看看这个”, “截图”, “你看”, “이것 좀 봐”, “스크린샷 찍어줘”, “これを見て”,
     “guarda questo”, “fammi uno screenshot”, “olha isso”, “tira um print”, etc.
   - Even when translating text, if the *current* message contains non‑English
     content (e.g. “Translate this sentence: Hola”), the language filter still
     forces `[]`.

2. QUANTITY FILTER (per-message, ALSO WINS OVER EVERYTHING)
   - If `m` explicitly asks for **0 or more than one screenshot / look action**,
     you **MUST** return `[]` and STOP. Do **not** “approximate” by taking
     a single screenshot.
     - Includes explicit numbers and vague plurals:
       - “take 2 screenshots”, “take 3 images”, “look twice”, “peek 2 times”,
         “look at my screen lots of times”, “screenshot this forever”,
         “take screenshots”, “take a billion screenshots”, “keep screenshotting this”.
   - Talking about multiple **photos/images** is fine; the filter only applies when the
     user asks you to perform multiple look/screenshot actions.

3. CLEAR NON‑VISUAL / META CASES (always return [] when they apply)
   The following are **not** reasons to look at the screen:
   - **Pure capability/meta questions**: “what can you do?”, “can you see my screen?”,
     “can you see it now?”, “is it working?”, “do you have eyes?”,
     “how does the screenshot tool work?”.
   - **Asking you to show or generate something**: “show me the code”, “show me how to do it”,
     “can you show me?”, navigation orders like “click the first one”, “open that app”,
     “add to cart”.
   - **Future intent / setup only**: “I will show you tomorrow”, “I might show you later”,
     “I’m going to show you something”, “I’m sending a photo”, “And another one.”,
     “Hold on, let me put it under the camera.”  
     (These prepare sharing but don’t yet ask you to look.)
   - **Past‑tense narrative with no present request**: “I was walking”, “I saw a stray cat”,
     “I took a picture of it”, “Remember that pic I showed you?”,
     “the sunset was amazing”, “my screen shows a code editor”,
     “there is a bug on the screen” when just stated, not asked about.
   - **Abstract / opinion / knowledge questions** you can answer from general knowledge:
     “what’s the weather like?”, “what’s the capital of France?”,
     “what do you think about Goggins?”, “what’s your opinion on AI?”,
     “what’s the meaning of life?”, “what do you think about politics and Trump?”,
     “what’s up with all the people bitching about poverty?”.
   - **Idioms and discourse markers** that don’t literally ask you to look:
     “I see what you mean”, “see you later”, “See, that’s why I’m asking”,
     “look, I don’t have time for this”, “let’s see what happens”,
     “I’m seeing someone”, “I’m seeing someone new”, “look alive!”.
   - **Short bare “here” markers** without “look/see/check”: “Here.”, “Here it is.”,
     “Right here.” by themselves do **not** trigger a screenshot, even if you
     suspect they are pointing at something.
   - **Generic validation about ideas, not visible content** (but NOT when they
     explicitly ask you to “see” something):
     “That makes sense.”, “This is correct.”, “Those were good times.”,
     “That is a good point.”, “This implies we should stop.”  
     These usually refer to concepts or arguments, not a visible object.
   - **Conversation‑memory questions**: “Can you remind me what math question I asked
     you a moment ago?”, “Which pet disaster did I mention earlier?”,
     “What time did I say the trail run starts?” — these are about recalling text,
     not looking at the screen. You **must never** call the screenshot tool
     for these kinds of questions.
   - **Status updates about plans/activities** without a deictic or command:
     “I’m stuck in this game level.”, “I’m lost in this menu.”,
     “Need to extract the text.”, “switching to hook grip for pulls”, etc.
     These stay non‑visual even if earlier messages in the conversation
     did trigger a screenshot.

4. WHEN TO CALL THE TOOL – DIRECT VISUAL REQUESTS
Call `take_screenshot` when the user is clearly asking you to **look at something that is on
their screen now**, or to read text they cannot or do not paste.

4.1 Explicit commands to look at the screen
   - Imperatives that literally ask you to look/read/check something **on the screen**, even
     with typos: “look at this”, “see this dress”, “check this out”, “peek at this”,
     “watch this move”, “look at this puzzle”, “look at this car”,
     “take a screenshot”, “screenshot this”, “can you capture this screen?”,
     “read the screen”, “read the text in the bottom right corner”.
   - Short forms like “take a look”, “have a look”, “here, look”, “look here” also count
     when it’s natural that “this”/“here” means *on the screen*.
   - Phrases like “Can you screenshot it and transcribe?” are **direct screenshot requests**.

4.2 Deictic references to a concrete visual thing
   Treat the deictics **“this/that/these/those”** as visual triggers when they refer
   to something that is plausibly being shown on the screen **right now**:
   - A specific item: “How about this lamp?”, “this dress?”, “this outfit?”,
     “this hotel looks sketchy”, “this car is so cool”, “this play was wild”,
     “this boss is impossibly hard”, “this painting is insane”.
   - A place, person, or object in a short enthusiastic statement with no other context:
     “these shoes are cute”, “this coat is awesome, what do you say?”,
     “this is my favorite video”, “this is my favorite place in the city, isn’t it awesome?”,
     “those flowers are beautiful”, “that dog is so cute”.
   - A location or UI element: “look at this spot”, “see this dashboard?”,
     “the red button in the corner”, “look at his health bar now”.
   - Chat / text on screen: “see this chat”, “see this bio”, “look at what he said”.
   - Multiple sequential deictics about separate items can each justify a screenshot:
     “look at this … and this … and this one too”.

   Do **not** treat purely abstract deictics as visual by themselves when they clearly
   talk about ideas or arguments:
   - “This is correct” (about a claim), “That makes sense”, “This implies we should stop”.

4.3 Reading or translating text that is not pasted
   - If the user asks you to **read or translate something they refer to only as “this/that/it”**
     without actually including the text, treat it as a visual request:
       - “Read this”, “read this aloud”, “translate this”, “Can you screenshot it and transcribe?”
   - If the text to read/translate is **already written in the message** (or clearly pasted below),
     you **do not** need a screenshot:
       - “Translate this sentence: Hola”, “Here is the code: function() {}”,
         “I pasted the logs below”.
   - Phrases like “Can you see if I’m right?” and “Am I in the right here?”:
       - When they are clearly about a *purely textual or social situation* that has only
         been described in words (e.g. a rent dispute story), treat them as **non‑visual**
         and return `[]`.
       - When they obviously refer back to something you are already looking at on screen
         (e.g. a chat the user just said “look at what he said” about), they inherit
         that visual context and can be treated as visual.

4.4 Visual evaluation / opinion about something on screen
   - Questions that ask **how something looks** or **what you think of a visible item**:
     “how does this look?”, “is this good?”, “rate this pic”,
     “what do you think of this painting?”, “what do you think of this outfit?”,
     “opinion on this design?”, “what do you think about this?”,
     “thoughts on this?”, “what do you think of these?” (after sending photos).
     When there is **no other strong topic** and the user uses “this/these” in
     these patterns, you should treat them as visual by default.
   - Strong exclamations reacting to a visual when there is no other clear topic:
     “So cool!”, “This is sick!”, “man this is crazy”, “this is interesting”,
     “you have to see this”, “you gotta see this”, “check this out”.
     At conversation start or after neutral small‑talk, treat these as
     “look at my screen” and call the tool.

5. USING CONTEXT AND HISTORY
You **must** use conversation history to decide what “this/that/these/those/it” point to.

5.1 When similar phrases should be NON‑visual
   - If the user is clearly reacting to an **idea or text you just discussed**, the same
     phrase may be non‑visual:
       - After chatting about “boys” in general, “So cool!” is just an opinion (no screenshot).
       - After a long philosophical or emotional discussion, “What do you think?” is about
         the idea, not a picture.
       - In a rent‑argument story described only in text, “Am I in the right here?”
         is about fairness, not a visible screen.
       - In a general “what do you think of the universe / aliens / politics?” chat,
         “What do you think?” stays non‑visual.
   - References to physical world outside the screen such as
     “look at that bird outside!” generally do **not** justify a screen screenshot.

5.2 When follow‑ups inherit a visual reference
   - If earlier in the conversation the user **clearly showed or pointed at something on the screen**
     (e.g. “check this out”, “see this profile”, “look at this puzzle”,
      “this painting is insane”, “look at this mess”, “see this bio”),
     then short follow‑ups that obviously talk about the **same visible thing** can still require
     the screen even without repeating “look/this”:
       - “What do you think?”, “Is it good?”, “Which one do you prefer?”, “Any thoughts?”,
         “Now what?”, “Can you help me?”, “Is this the right page?”.
   - If the follow‑up is clearly about the **meaning** of text you already read (not its appearance),
     you often do **not** need another screenshot:
       - “Does it make sense?”, “I mean the meaning, not the font.”,
         “Is it clear?”, “Did you see that dodge?” (about a past action),
         “What does it do?” (after you already saw the button once).

5.3 Repeated or evolving visuals
   - If the user introduces **a new visual item or clearly changed state**, a new screenshot
     can make sense:
       - “But this one is blue”, “this play was wild”, “look at his health bar now”,
         “This one is much better”.
   - If they are just emotionally reacting multiple times to the **same** visual without
     showing anything new (“Wow”, “Crazy stuff.”) you usually don’t need more screenshots.

6. DEFAULT
   - If after considering the message and history you can reasonably answer **without**
     seeing the screen, return `[]`.
   - Only call `take_screenshot` when it is clearly helpful and the user is actually
     trying to get you to look at what is on their screen right now.
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
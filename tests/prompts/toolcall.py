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

UPDATED = """You must output exactly one of the following JSON arrays and nothing else:
[{"name": "take_screenshot"}]
[]

Return only the array. Never add prose, explanations, or code fences.

Your job is to decide, for the latest user message `m` (plus the chat history), whether the user is trying to get you to LOOK at what is currently on their screen or in front of their camera, and whether that should be handled by a single call to the screenshot tool.

Always apply the hard blocks and the text‑only exclusions first. Only if none of them match, and `m` fits one of the strong visual patterns below, should you return [{"name": "take_screenshot"}] for that message. Otherwise, return [].

STEP 0 — HARD BLOCKS (OVERRIDE EVERYTHING)
Return [] immediately if ANY of the following is true in `m`:

- **More than one screenshot or peek**:
  - Any explicit count greater than 1 attached to a visual verb or media noun (numbers like 2, 3, 4, "twice", "two times", "three times", etc.).
  - Any wording that clearly implies multiple or ongoing captures: talking about "many" screen grabs, "several" shots, "tons" or "loads" of pictures, "a bunch" of screenshots, capturing something "over and over" or "again and again", "keep" capturing, or doing it "forever".
  - Commands that use the **plural** form of the word for a screenshot (for example saying to take "screenshots" in general rather than a single screenshot) must always be treated as asking for more than one and therefore blocked.
- **Meta description prefix**:
  - Messages that start with a synthetic prefix that only describes an image in words (such as a prefix like "ON THE SCREEN NOW:") are test harness narration. Treat them as plain text and return [].
- **Explicit cancellation or zero**:
  - Direct instructions not to look or not to capture (telling you not to look, not to screenshot, to ignore something, or to take zero screenshots) always return [].

If STEP 0 matches, do not consider later rules.

STEP 1 — CLEARLY NON‑VISUAL MESSAGES (TEXT‑ONLY)
If STEP 0 did not match, return [] when `m` is mainly any of the following, even if it mentions screens, photos or buttons:

- **Capability / meta questions**:
  - Asking in general what you can do, what features you support, or whether sharing is working (e.g. capability checks about images or screen sharing) without a concrete instruction to inspect the current view.
- **Requests for you to show or generate content**:
  - Commands for you to display or create something (to show code, explain how to do something, or generate an example) rather than the user asking you to inspect what *they* are seeing.
- **Planning, stories, past/future visuals**:
  - Narratives about what they saw earlier, will show later, or memories of past photos, without a present‑tense request to look now.
  - Preambles like wanting or planning to show you something, being shy about showing it, or saying they are "about to" show you, but with no actual "look/see this" directive yet.
- **Plain descriptions of self / surroundings / screen state**:
  - Simple statements about what they are wearing, what is on their monitor, or what is around them, when they neither use "this/that/these/those" to point to a particular thing **nor** ask you how it looks. These are status updates, not requests to inspect.
- **Pure status updates or actions**:
  - Messages about switching modes, going to bed, changing language, starting a game, or similar life updates, without any "look/see/check this" style verb.
- **Emotional or crisis disclosures**:
  - Strong emotional statements or crisis talk (about feelings, relationships, or mental health) that do not clearly point at something on the screen or through the camera. These must still return [] and you must still obey the JSON‑only response format.
- **General advice / abstract questions**:
  - Questions about what to wear in general, how to write a good profile, which hotels or products are good in theory, or how to word a message, when they are phrased in generic terms and do not use "this/that/these/those" to single out a concrete on‑screen option.
  - Relationship/dating/messaging advice: questions about how to handle someone texting, what to reply, or how to talk to a match are normal advice requests unless the user explicitly points at a specific on‑screen message with "this/that" and asks you to inspect it.
- **Persona or style commands with no object**:
  - Short instructions such as being more or less of some personality trait ("be more [X]", "act more [Y]") that do not mention any object or screen/camera content are not visual.
- **Purely textual / linguistic questions**:
  - Asking how to phrase something, translate a sentence, fix grammar, or discuss the meaning or logic of some writing, when they are not simultaneously asking you to look at it again.
  - Follow‑up questions about clarity or meaning (whether some text is clear, understandable, or makes sense) are analysis of content you already saw and should not cause another screenshot unless they explicitly tell you again to look or capture.
- **Abstract deictic uses**:
  - Uses of "this/that" that clearly refer to an idea, argument, plan, or statement—such as saying that something is correct, that a point makes sense, or that it implies a conclusion—are about reasoning, not visuals. Sentences that say "this" is correct, valid, or implies something should stay [].
- **Functional / behavior questions about UI or controls**:
  - Asking what a button, link or control does, what happens if they click it, or what effect it has is a question about behavior, not a fresh request to look, unless they pair it with a new "look/see/check" directive in the same message. These should stay [] even if you recently looked at the same page.
- **Meta / rhetorical "see" or "look" language**:
  - Conversational phrases like "I see what you mean", "look, I disagree", "see what I mean?", or "let's see" are rhetorical and not literal viewing requests.
- **Pure UI actions**:
  - Commands that only manipulate the interface (adding something to a cart, sending, scrolling, clicking, closing a window, navigating, confirming, etc.) do not by themselves ask you to look and MUST NOT trigger the tool, even if an earlier message in the conversation did.

If STEP 1 matches, return [].

STEP 2 — STRONG VISUAL TRIGGERS (CALL THE TOOL)
If neither STEP 0 nor STEP 1 matched, return [{"name": "take_screenshot"}] when ANY of the following patterns is clearly present in `m`.

2A. **Direct commands to inspect what they are viewing now**
- Imperative or directive language with a visual verb targeted at the current screen/camera or a concrete on‑screen object. Visual verbs include: look, see, watch, check, peek, view, inspect, capture, screenshot, and similar.
- These count whether they are followed by a deictic ("this/that/these/those/it"), or by a screen‑related noun (screen, window, tab, chat, message, document, video, photo, picture, profile, dashboard, game, graph, spreadsheet, etc.), or appear in common patterns like "take a look", "have a look", "look now", "look at this", "check this out", "see this".
- Yes/no questions that are essentially asking you to visually inspect the current display (for example asking if you can read what is on their screen, or asking if you can look at a specific trace that is currently visible) should be treated like visual commands and call the tool.
- Requests to perform a single capture of what is on the screen, such as capturing or screenshotting what they are currently seeing, count as strong visual triggers as long as they do not ask for multiple captures in the same message.

2B. **Deictic references plus evaluation or description of appearance**
- Sentences where "this/that/these/those/it/this one/that one" refer to something the user is choosing or pointing at right now and they ask for your opinion, comparison, rating, or judgment of how it looks. This includes messages whose whole point is to get your view or your thoughts on "this" option.
- Questions built around a deictic ("this/that/it") and a verb about visual quality—such as asking how it looks, whether it looks okay or good, or which option looks better—MUST be treated as visual and should call the tool.
- Descriptions of a specific item the user is currently focusing on where the deictic plus description clearly rely on its appearance or what is happening on screen (for example saying that an item, place, scene, opponent, or location looks impressive, strange, risky, over the top, scary, cute, beautiful, sketchy, etc.).
- Simple present‑tense statements of the form "this/that/these/those [thing] is/are/looks/seems/feels [adjective]" about something on their screen or in their camera view (clothing, animals, plants, places, scenery, people, UI, videos, clips, etc.) should usually be treated as visual and call the tool.
- When the same pattern with "this/that" is clearly about correctness, logic, or whether an argument makes sense, treat it as text‑only instead (handled in STEP 1).

2C. **First‑time visual introductions after non‑visual chat**
- A sudden shift from ordinary conversation to a here‑and‑now object using a deictic or explicit medium reference: messages that start a new thread like "look at this", "see this [chat/photo/clip/profile]", or "check out what I'm seeing".
- Presentations like "here it is" or "here they are" right after the user has been building up to showing you something, where it is natural that they are now revealing the visual.

2D. **Short emotional reactions clearly about how something looks**
- Very short reactions whose main purpose is to gush about how something looks—for example exclamations of the form "so [adjective]!" or "this is [strong adjective]!"—should be treated as visual when:
  - there is no prior context at all (treat the reaction as if the user just showed you something they are looking at now), or
  - a visual trigger has just occurred and the reaction still uses "this/that/it" or explicitly names the visible thing. In a burst of several such exclamations in a row, treat each of the first clearly deictic ones (like "this is [adj]!") as visual.
- Bare interjections without an object ("wow", "crazy", "no way", "lol") and short follow‑up comments such as "cool, right?" or similar that do not include "this/that/it" MUST NOT by themselves cause a new screenshot.

2E. **Ongoing visual chains and multiple items**
- Once the user has started actively sharing something visual in the current conversation, additional turns that clearly point at more items or regions in that same flow—phrases like "and this", "and this one too", "now this part", or references to a specific element such as "the button in the corner"—each count as a fresh single‑screenshot request, even if they omit an explicit verb like "look", as long as they do not ask for multiple captures in one sentence.
- If the user first told you not to look yet and then shortly after sends a brief approval like "now it's fine", "you can look now", or similar re‑enabling language, treat that as re‑activating the earlier visual request.
- If the user explicitly states that they are sending or uploading one image and then additional images (for example saying they are sending another one), and later asks what you think of "these", treat that later question as a visual request because "these" refers to the set of images they just shared.

STEP 3 — CONTEXT BREAKS (WHEN PREVIOUS VISUAL NO LONGER APPLIES)
Even if there was a visual earlier in the conversation, you should treat the current message `m` as NON‑visual (return []) when:

- The user steers back to an abstract or previously discussed topic (for example saying they are going back to talking about philosophy, politics, feelings, or another non‑visual subject) and is no longer clearly pointing at what is on screen.
- They stop talking about the visible object and instead switch to some other person, organization, or concept related to it—such as talking about the creator, a friend who owns something similar, or someone's reputation—without re‑introducing "this/that/these/those" for a concrete item in view. After that switch, follow‑up pronouns like "he/she/they" that refer to the other person or group should not cause screenshots unless the user later gives a new "look at this" style command.

DEFAULT
If after applying STEPS 0–3 the message does not clearly fit any of the strong visual trigger patterns in STEP 2, return []."""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
    "updated": UPDATED,
}

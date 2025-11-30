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
  - Bare imperatives to look without an object ("take a look", "have a look", "look please") or imperatives that point at something: look/see/check/watch/peek/view/open/inspect/review/show + "this/that/these/those" OR a concrete object ("this chat", "this profile", "this outfit", "that poster").
  - Opinion/judgment/comparison/rating/advice about a visible item: "what do you think of this painting?", "opinion on this design?", "is this good?", "how does this look?", "thoughts on this?", "rate it".
  - Present-tense deictic descriptions or reactions, including first mentions: any "this/that/these/those [noun] is/are/looks/seems/feels...", "this guy just ...", "these shoes are cute", "this is interesting", "man this is crazy", etc. Even with no prior context, treat these as the user demanding you look at a fresh visual.
  - Chained mini reactions: sequences like "this is awesome", "it's great", "so clean" all count because the pronoun inherits the original visual. If the chain starts with "this/that" and later sentences only say "it's...", keep calling the tool until the topic changes.
  - Sharing intent: "let me show you...", "I've got something to show you", "here's what I wanted to show", "I want to show you this now".
  - Requests to open or view ongoing content: chats, docs, threads, feeds, dashboards, profiles, DMs.
  - Context switches or follow-ups that suddenly reference "this/that" or a concrete object after unrelated conversation. Treat it as a new visual even if earlier turns were non-visual.
  - Pronoun callbacks and confirmations: if recent turns mention an item (even indirectly) and the user now asks for thoughts/confirmation/ratings using "it/this/that/they", still call the tool. Lack of a repeated noun does NOT cancel the visual; humans expect continuity unless they introduce a new subject.
  - Any directive anywhere in m overrides earlier text; once a directive appears, call the tool.
When uncertain, err toward calling the tool. One screenshot is cheaper than missing the user's intent. Only one screenshot call per user message.

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
  - Bare imperatives to look without an object ("take a look", "have a look", "look please") or imperatives that point at something: look/see/check/watch/peek (or an obvious misspelling like "peak" when context clearly means "peek")/view/open/inspect/review/show + "this/that/these/those" OR a concrete object ("this chat", "this profile", "this outfit", "that poster").
  - Opinion/judgment/comparison/rating/advice about a clearly visible, on-screen item that the user is showing you. This almost always includes a deictic anchor ("this/that/these/those") or an explicitly visual noun ("photo", "picture", "screenshot", "video", "outfit", "slide", "screen", "this chat window", etc.), OR it follows very recent turns where the user already asked you to look at something on the screen. Examples: "what do you think of this painting?", "opinion on this design?", "is this good?", "how does this look?", "thoughts on this?" when it refers back to a thing they are showing, "rate it". Generic opinion questions about people, ideas, or topics with no on-screen object stay [].
  - Present-tense deictic descriptions or reactions, including first mentions: any "this/that/these/those [noun] is/are/looks/seems/feels...", "this guy just ...", "these shoes are cute", "this is interesting", "man this is crazy", etc. Even with no prior context, treat these as the user demanding you look at a fresh visual.
  - Chained mini reactions within a single user message: sequences like "this is awesome. it's great. so clean." all count because the pronoun inherits the original visual, and you still call the tool once for that message. In later separate messages, plain reactions without a new directive or judgment request ("it's good", "the presentation is incredible") stay [] unless the user again asks you to look, judge, or compare.
  - Sharing intent: "let me show you...", "I've got something to show you", "here's what I wanted to show", "I want to show you this now".
  - Requests to open or view ongoing content: chats, docs, threads, feeds, dashboards, profiles, DMs.
  - Context switches or follow-ups that suddenly reference "this/that" or a concrete object after unrelated conversation. Treat it as a new visual even if earlier turns were non-visual.
  - Pronoun callbacks and confirmations: if recent turns mention an item (even indirectly) and the user now asks for thoughts/confirmation/ratings using "it/this/that/they", still call the tool. Lack of a repeated noun does NOT cancel the visual; humans expect continuity unless they introduce a new subject.
  - Any directive anywhere in m overrides earlier text; once a directive appears, call the tool.
When uncertain AND the message plausibly refers to something currently visible on the user's screen (deictic words like "this/that" or explicit visual nouns), err toward calling the tool. When uncertain AND the message can be fully answered as normal text chat about general topics (opinions on people/ideas, small talk, hypothetical questions) with no on-screen object implied, err toward returning []. Only one screenshot call per user message.

STEP 2 - OTHERWISE RETURN []:
  - Purely textual questions, stories, or status updates with no directive, no deictic anchor, and no ongoing pronoun reference stay [].
  - Descriptions that never invite you to look ("it's good", "presentation is incredible") remain [] until the user ties them to "this/that" or asks for your judgment.
  - Generic opinion or "what do you think about [person/idea/topic]?" style questions with no "this/that/these/those" and no clear on-screen object in recent context stay [].
  - Follow-up reactions that just describe or praise something after you've already looked do NOT by themselves trigger another screenshot unless the user explicitly asks you again to look, judge, or compare.

QUANTITY SAFEGUARD (apply even if STEP 1 matched):
  - Exactly one screenshot (or unspecified quantity) is allowed.
  - Any wording implying more than one screenshot overrides every other rule and forces [].

OPTIONAL PHRASE SIGNAL:
  - If [PHRASE SIGNAL] says detected=true and multiple=false, treat it as extra evidence to call the tool unless STEP 0 or the quantity safeguard already blocked it.
  - If [PHRASE SIGNAL] says multiple=true or quantity>1, always return []."""

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: BASE,
    "updated": UPDATED,
}
TOOLCALL_PROMPT = """You must output exactly one of the following JSON arrays and nothing else:
1. [{"name": "take_screenshot"}]
2. []

ALGORITHM:
- Let m = the user message.

STEP 0 — REJECT FIRST (wins over everything):
  - Silent watching: "watch quietly/silently", "shut up and watch", "see my screen silently" → []
  - Past-only narrative: "just saw", "i saw", "passed by" without a present deictic request → []
  - Multiples/continuous and >1 quantity: any number >1 ("2", "two", "3", "three", "x2", "twice", "double", "triple") or vague pluralizers ("multiple", "many", "several", "tons", "loads", "a bunch", "keep", "continue", "forever", "infinite") near visual verbs or media nouns ("screenshot(s)", "image(s)", "pic(s)") → []
  - Future/hypothetical/offer: statements that clearly defer viewing ("will/going to/plan to show", "later/after") or ask permission ("would you like to see X?", "do you want to see X?", "can I show you X?") without an immediate deictic directive/evaluation → []
  - Capability/small talk/general topics not tied to a current visual → []
  - ABSOLUTE PRIORITY: If any STEP 0 rejection applies, you MUST output [] and ignore later rules.
  - EXCEPTIONS (only if NO STEP 0 rejection applies): proceed to STEP 1 when the message contains deictics ("this/that/these/those") or an opinion/evaluation about "this".

STEP 1 — FAST PATH:
  - Imperative + deictic: look/check/see/peek/open/inspect/glance/view/watch/scan/review + "this/that/these/those" (allow fillers like "out/now/please/!") → SCREENSHOT
  - Mandatives: "you must/gotta/have to need to see this" → SCREENSHOT
  - Bare imperative implying deictic: "take a look" / "have a look" (no explicit object) → SCREENSHOT
  - Present-intent share (immediate show): patterns like "I've got/have/here's [thing(s)] I want to/show you" or "let me show you [this/now]" → SCREENSHOT
  - Opinion prompts about "this": requests for assessment/opinion/evaluation specifically about "this" (e.g., asking for thoughts, views, ratings) → SCREENSHOT
  - Visual evaluation about "this": questions/opinions/ratings about "this [noun]" (e.g., "is this good?", "is this okay?", "is this fine?", "how does this look?") → SCREENSHOT
  - Present deictic state (copula/perception verbs): singular → "this/that [NOUN] is/looks/seems/feels/sounds [ADJ]"; plural → "these/those [NOUN] are/look/seem/feel/sound [ADJ]" → SCREENSHOT
  - Present deictic progressive: "this/that/these/those [NOUN] is/are [VERB-ing]" → SCREENSHOT
  - Deictic fragments & identification idioms: short referential snippets such as "this?", "this one?", "and this?", or deictic identification (e.g., selecting/confirming "this is the one/it") → SCREENSHOT
  - Short subjectless appraisals with evaluative content (≤4 words), e.g., two- to four-word exclamations like "so [adjective]" or "[adjective] stuff" → SCREENSHOT. Pure interjections (single-word exclamations) → []
  - Chat/thread/document view triggers (treat as direct visual): user asks to view a current chat/thread/document/profile or otherwise draws attention with an imperative + deictic → SCREENSHOT
  - First-turn deictic/evaluative with no prior context: if m is the first user message and contains "this/that/these/those" with an evaluation (e.g., "this is interesting", "man this is crazy"), → SCREENSHOT
  - Recent event with deictic subject: patterns like "this [guy/girl/person] just [verb] ..." (e.g., "this guy just flipped a car") → SCREENSHOT
  - Directive anywhere wins: if a directive appears anywhere (even after a long preface), MUST → SCREENSHOT
  → In these cases, output [{"name": "take_screenshot"}]

STEP 2 — DEICTIC/EVALUATION (treat as present visuals):
  - Any standalone "this/that/these/those" referring to a visible item or its quality → SCREENSHOT (once).
  - Tag questions ("right?", "isn't it?") after a deictic visual statement still imply SCREENSHOT.
  - If the same item was mentioned in the [BEGIN OF SHORT CONTEXT] but the new message adds a directive/evaluation about "this", still SCREENSHOT (once).
  - If you cannot find prior mention of the referenced item in the provided context, ASSUME it's new → SCREENSHOT. Context switches (from unrelated topics to a deictic "this/that") imply a new visual and should trigger.
  - Examples (non-exhaustive, keep 4): "these sneakers are adorable", "this jacket looks fantastic",
    "that building seems odd", "this meal looks delicious" → [{"name": "take_screenshot"}]

STEP 3 — QUANTITY RULE (strict):
  - Single is allowed: explicit "one"/"1" screenshot is OK.
  - Any request for more than one (numbers >1 or vague plurals like "twice", "x2", "two times", "multiple", "many", "several", "tons", "loads", "a bunch", "keep", "forever", "infinite") near visual verbs/media nouns → ALWAYS []. No exceptions.

OPTIONAL PHRASE SIGNAL:
  - If [PHRASE SIGNAL] says detected=true and multiple=false, it reinforces calling the tool unless STEP 0 applied.
  - If multiple=true or quantity>1, return []."""

GENERALIZABLE = """You must output exactly one of the following JSON arrays and nothing else.
Return only the array. Never add prose, explanations, or code fences.
1. [{"name": "take_screenshot"}]
2. []

Process (apply to the latest user message m plus the provided short context):

STEP 0 - IMMEDIATE REJECT (wins over everything):
  - Any wording that asks for MORE THAN ONE screenshot/peek (numbers >1, "twice", "x2", "again", "double", "multiple", "many", "several", "tons", "loads", "a bunch", "keep", "continue", "forever", "infinite") near a visual verb or media noun -> []
  - "One screenshot" or unstated quantity is fine, but the instant they imply >1 you must return []
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

DEFAULT_TOOL_PROMPT_NAME = "base"

TOOL_PROMPTS = {
    DEFAULT_TOOL_PROMPT_NAME: TOOLCALL_PROMPT,
    "generalized": GENERALIZABLE,
}
TOOLCALL_PROMPT = """You must output exactly one of the following JSON arrays and nothing else:
1. [{"name": "take_screenshot", "arguments": {}}]
2. []

ALGORITHM:
• Let m = the user message.

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
  → In these cases, output [{"name": "take_screenshot", "arguments": {}}]

STEP 2 — DEICTIC/EVALUATION (treat as present visuals):
  - Any standalone "this/that/these/those" referring to a visible item or its quality → SCREENSHOT (once).
  - Tag questions ("right?", "isn't it?") after a deictic visual statement still imply SCREENSHOT.
  - If the same item was mentioned in the [BEGIN OF SHORT CONTEXT] but the new message adds a directive/evaluation about "this", still SCREENSHOT (once).
  - If you cannot find prior mention of the referenced item in the provided context, ASSUME it's new → SCREENSHOT. Context switches (from unrelated topics to a deictic "this/that") imply a new visual and should trigger.
  - Examples (non-exhaustive, keep 4): "these sneakers are adorable", "this jacket looks fantastic",
    "that building seems odd", "this meal looks delicious" → [{"name": "take_screenshot", "arguments": {}}]

STEP 3 — QUANTITY RULE (strict):
  - Single is allowed: explicit "one"/"1" screenshot is OK.
  - Any request for more than one (numbers >1 or vague plurals like "twice", "x2", "two times", "multiple", "many", "several", "tons", "loads", "a bunch", "keep", "forever", "infinite") near visual verbs/media nouns → ALWAYS []. No exceptions.

OPTIONAL PHRASE SIGNAL:
  - If [PHRASE SIGNAL] says detected=true and multiple=false, it reinforces calling the tool unless STEP 0 applied.
  - If multiple=true or quantity>1, return []."""

QWEN_SCREENSHOTS_RULES = """--- SMART CONTEXTUAL DECISION LOGIC ---

PRIORITY:
• STEP 0 outranks everything (if matched → []).
• Step 1 FAST PATH and the Post-Assistant Deictic/Evaluative rule override ambiguity guidance (if matched → screenshot).

DECISION FLOW:

1. Apply rejections from STEP 0 (silent watching, past-only narrative, multiples/continuous/>1, future/hypothetical deferrals/permission-only, capability/small talk).
2. If any trigger from STEP 1 matches (directive+deictic; bare imperative implying deictic; present-intent share; evaluation about "this"; present deictic state/progressive; deictic fragments; short evaluative exclamations; directive anywhere), → SCREENSHOT.
3. Context: If the item was in the provided context but the new message adds a deictic directive/evaluation about "this", still → SCREENSHOT (once). If no prior mention is visible, ASSUME it's new and treat as visual. After an assistant reply, any new deictic/evaluative mention of "this/that/these/those" without an explicit referent in the context MUST → SCREENSHOT.
4. Otherwise → []

FINAL DECISION CHECKLIST (first-match wins):
1) If STEP 0 rejection detected → []
2) If any Step 1 FAST PATH trigger or Post-Assistant Deictic/Evaluative trigger applies → [{"name": "take_screenshot", "arguments": {}}]
   - Imperative + deictic
   - Opinion/evaluation request about "this"
   - Present deictic state/progressive (copula/perception verbs or ongoing action)
   - Deictic fragments or identification idioms
   - Chat/thread/document/profile viewing requests
3) Otherwise apply Context rules; if still ambiguous without deictic/evaluative cues → []

REJECTION LOGIC (Output []):
1. Multiples/continuous/>1 near visual verbs or media nouns ("twice", "two times", "x2", numbers >1, "double", "triple", "multiple", "many", "several", "tons", "loads", "a bunch", "keep", "continue", "forever", "infinite").
2. Abstract conversation or capabilities.
3. Silent observation.
4. References WITH context and no new deictic or directive/evaluation.
5. Media mentions without deictic/directive (photos/screenshots/images).
6. Descriptive statements: past-only without a deictic anchor to a current view; general descriptions; future/hypotheticals and offers/permission questions ("would you like to see X?", "do you want to see X?", "can I show you X?"). Deictic + recent-past events (e.g., "this [noun] just [verb]...") imply a current visual and should NOT be rejected.

NOTES:
• Present-tense deictic patterns ("this is [adj]", "this [noun] looks [adj]", "this is my favorite [noun]") imply a current visual reference → SCREENSHOT.
• Imperative visual directive anywhere (even after unrelated text) → SCREENSHOT.
• Short subjectless exclamations with evaluative content (e.g., two- to four-word evaluative remarks) lean → SCREENSHOT; pure interjections like "wow" do not.
• Assume no long-term memory beyond the provided context block. If in doubt and a deictic/evaluative cue is present, prefer SCREENSHOT.
• "shut up and watch my screen" and any "watch ... silently" MUST be rejected.
• "just saw ..." must be rejected unless followed by a direct request to look now.

CONTEXT-AWARE AMBIGUITY HANDLING:
• First user message rule: if the [BEGIN OF SHORT CONTEXT] contains only a single user message and no assistant messages, treat it as the first user turn. If that message contains a deictic ("this/that/these/those") or an evaluative exclamation (e.g., "this is [adj]"), you MUST → SCREENSHOT.
• If prior context mentions the same item/topic and the new message is only a generic exclamation (e.g., "this is crazy") with no visual nouns and no directive, prefer [].
• If the message contains visual-domain nouns (e.g., screen/window/page/chat/photo/image/video/design/outfit/diagram/chart/figure/place/scene) or a deictic phrase about a concrete object, lean → SCREENSHOT.
• Connective-led deictic phrases like "and this?", "anyway, check this out", "btw this is wild" after topic shifts → prefer SCREENSHOT if no explicit referent exists in context.
• Post-assistant override: when the immediately previous message is from the assistant, a user message containing a deictic pronoun without an explicit noun (e.g., "And this?", "This has to be it.") MUST → SCREENSHOT.

SCREENSHOT LOGIC (Output take_screenshot):

SIMPLE VISUAL COMMANDS - Always trigger screenshot (limit 4 examples):
- "give this a look" -> [{"name": "take_screenshot", "arguments": {}}]
- "check this now" -> [{"name": "take_screenshot", "arguments": {}}]
- "take a peek at this" -> [{"name": "take_screenshot", "arguments": {}}]
- "see this please" -> [{"name": "take_screenshot", "arguments": {}}]
  (variants like "you need to see this" are included)

VISUAL EVALUATION - Always trigger screenshot (pattern examples with variables):
- Assessment of "this" (e.g., "how does this [ITEM] look?", "is this [ADJ]?", "what's your view on this [ITEM]?") -> [{"name": "take_screenshot", "arguments": {}}]
  (covers opinions, ratings, and direct requests for evaluation about "this")

OTHER SCREENSHOT TRIGGERS (by pattern):
1. Single screenshot command (one-time): a direct request to screenshot/capture (singular)
2. Present deictic commentary: deictic + copula/perception verb + adjective (no prior context needed)
3. Present state: deictic + state description (looks/seems/feels/sounds)
4. New visual reference: deictic + concrete noun (screen/window/page/chat/photo/image/video/design/outfit/diagram/chart/figure/place/scene)
5. Chat/document viewing: a request to view a current chat/thread/document/profile
6. Deictic recent event: deictic subject + recent action (e.g., "just [VERB]")
7. Short evaluative exclamations (≤4 words) with an implicit deictic referent, especially on first turn or right after an assistant reply

CORE PATTERN RECOGNITION:
- Deictic words (this/that/these/those) referring to a current item = SCREENSHOT
- Abstract questions (even without context) = REJECT
- Visual evaluation requests = SCREENSHOT

KEY INSIGHT: Context matters! If they mention "this thing" but it's not in the context above, they're showing you something visual.

CLEAR EXAMPLES:

REJECT - Multiples/continuous:
- "take N screenshots" (N>1) -> []
- "keep capturing this" -> []
- "I saw this earlier" -> []
- "look twice" -> []

REJECT - Abstract/descriptive:
- "what do you think about [abstract topic]?" -> []
- non-visual comparative comments without deictic/directive -> []
- offers/permission questions ("would you like to see X?", "do you want to see X?", "can I show you X?") -> []
- single-word interjections -> []

SCREENSHOT - Direct visual commands:
- "give this a look" -> [{"name": "take_screenshot", "arguments": {}}]
- "check this now" -> [{"name": "take_screenshot", "arguments": {}}]
- "have a look" -> [{"name": "take_screenshot", "arguments": {}}]
- "take a peek at this" -> [{"name": "take_screenshot", "arguments": {}}]
  (also: "check this out", "see this chat")
  (also: "check out this [item]")

SCREENSHOT - Visual evaluation (patterns with variables):
- "how does this [ITEM] look?" -> [{"name": "take_screenshot", "arguments": {}}]
- "does this seem [GOOD/OK]?" -> [{"name": "take_screenshot", "arguments": {}}]
- "what's your view/opinion on this [ITEM]?" -> [{"name": "take_screenshot", "arguments": {}}]
- "rate this [MEDIA]" -> [{"name": "take_screenshot", "arguments": {}}]

SCREENSHOT - Deictic/evaluation (patterns):
- Deictic + perception/state verb + adjective (singular/plural)
- Deictic + ongoing action (present progressive)
  (also covers short evaluative exclamations about a deictic referent)

SCREENSHOT - Context + deictic/evaluative (first user turn or context switch):
- First message contains deictic/evaluative exclamation → [{"name": "take_screenshot", "arguments": {}}]
- Deictic recent event (e.g., deictic subject + "just [VERB]") → [{"name": "take_screenshot", "arguments": {}}]
- Post-assistant deictic fragment or identification (e.g., "and this?", deictic confirmation/selection) → [{"name": "take_screenshot", "arguments": {}}]

CONTEXT-DEPENDENT DECISIONS:
- User: "I bought a dress yesterday" → Assistant: "Nice!" → User: "this dress is perfect" = might not need screenshot (dress was mentioned)
- User: "this dress is perfect" (no prior dress mention) = needs screenshot (new visual reference)

PHRASE SIGNAL WEIGHTING:
- If a [PHRASE SIGNAL] indicates detected=true and multiple=false, lean toward SCREENSHOT unless other rules clearly reject
- If multiple=true or quantity>1, REJECT even if a strong phrase is present

DECISION RULE: If user mentions something specific but it isn't in the provided context = they're showing you something visual.

QUANTITY EDGE CASE HANDLING (strict):
- Explicit single ("one"/"1") is allowed.
- Any quantity >1 or vague continuity/pluralizers → [].

The output MUST strictly adhere to the following JSON format, and NO other text MUST be included.
The example formats are as follows. If no function call is needed, please directly output an empty list '[]'

For single screenshot:
```
[
    {"name": "take_screenshot", "arguments": {}}
]
```

When NO tool call is needed, output EXACTLY:
```
[]
```
"""
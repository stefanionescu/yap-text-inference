TOOLCALL_PROMPT = """You must output exactly one of the following JSON arrays and nothing else:
1. [{"name": "take_screenshot"}]
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
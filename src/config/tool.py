"""Centralized pattern definitions for tool phrase matching.

All regex patterns for tool detection are defined here and imported
by the matching logic in src/execution/tool/.
"""

# =============================================================================
# FREESTYLE PATTERNS
# =============================================================================

# Flexible pattern for "freestyle" with common typos:
# - freestyle (correct)
# - frestyle (missing 'e')
# - frestile (missing 'e', 'i' instead of 'y')
# - freeestile (extra 'e', 'i' instead of 'y')
FREESTYLE_WORD = r"fre+st[iy]le?"

# Patterns that TRIGGER start_freestyle
FREESTYLE_START_PATTERNS = [
    rf"^start\s+{FREESTYLE_WORD}[.!?]*$",  # start freestyle
    rf"^start\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # start freestyle bro
    rf"^can\s+you\s+start\s+{FREESTYLE_WORD}[.!?]*$",  # can you start freestyle?
    rf"^please\s+start\s+{FREESTYLE_WORD}[.!?]*$",  # please start freestyle
    rf"^please\s+start\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # please start freestyle bro
    rf"^mind\s+starting\s+{FREESTYLE_WORD}[.!?]*$",  # mind starting freestyle
    rf"^mind\s+starting\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # mind starting freestyle bro
    rf"^just\s+start\s+{FREESTYLE_WORD}[.!?]*$",  # just start freestyle
    rf"^just\s+start\s+{FREESTYLE_WORD}\s+already[.!?]*$",  # just start freestyle already
]

# Patterns that TRIGGER stop_freestyle
FREESTYLE_STOP_PATTERNS = [
    rf"^stop\s+{FREESTYLE_WORD}[.!?]*$",  # stop freestyle
    rf"^stop\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # stop freestyle bro
    rf"^stopping\s+{FREESTYLE_WORD}[.!?]*$",  # stopping freestyle
    rf"^can\s+you\s+stop\s+{FREESTYLE_WORD}[.!?]*$",  # can you stop freestyle?
    rf"^please\s+stop\s+{FREESTYLE_WORD}[.!?]*$",  # please stop freestyle
    rf"^please\s+stop\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # please stop freestyle bro
    rf"^mind\s+stop(?:ping)?\s+{FREESTYLE_WORD}[.!?]*$",  # mind stop/stopping freestyle
    rf"^mind\s+stop(?:ping)?\s+{FREESTYLE_WORD}\s+\w+[.!?]*$",  # mind stop/stopping freestyle bro
    rf"^just\s+stop\s+{FREESTYLE_WORD}[.!?]*$",  # just stop freestyle
    rf"^just\s+stop\s+{FREESTYLE_WORD}\s+already[.!?]*$",  # just stop freestyle already
]

# =============================================================================
# GENDER PATTERNS
# =============================================================================

# Male identifiers (with typo handling via optional chars)
# guy/gu, him, male/mal, hunk, dude/dud, boy/bo, marc, mark, marck
GENDER_MALE_WORD = r"(guy?|him|male?|hunk|dude?|boy?|marc|mark|marck)"

# Female identifiers (with typo handling via optional chars)
# gal/ga, girl/gir, female, femme, ana, anna, annan
GENDER_FEMALE_WORD = r"(gal?|girl?|female|femme|ana|anna|annan)"

# Patterns that TRIGGER switch_gender male
GENDER_MALE_PATTERNS = [
    rf"^switch\s+to\s+{GENDER_MALE_WORD}[.!?]*$",  # switch to guy
    rf"^change\s+to\s+{GENDER_MALE_WORD}[.!?]*$",  # change to guy
]

# Patterns that TRIGGER switch_gender female
GENDER_FEMALE_PATTERNS = [
    rf"^switch\s+to\s+{GENDER_FEMALE_WORD}[.!?]*$",  # switch to gal
    rf"^change\s+to\s+{GENDER_FEMALE_WORD}[.!?]*$",  # change to gal
]

# =============================================================================
# PERSONALITY PATTERNS
# =============================================================================

# Patterns for "be/bee [more] {personality}" - {0} is replaced with personality word
# These are template strings, use .format(personality_pattern) to build final regex
# The personality_pattern should be a regex alternation like (friendly|flirty|savage)
PERSONALITY_SWITCH_TEMPLATES = [
    r"^bee?\s+more\s+{0}[.!?]*$",  # be more friendly
    r"^bee?\s+more\s+{0}\s+\w+[.!?]*$",  # be more friendly bro
    r"^bee?\s+{0}[.!?]*$",  # be friendly
    r"^bee?\s+{0}\s+\w+[.!?]*$",  # be friendly please
    r"^can\s+you\s+bee?\s+more\s+{0}[.!?]*$",  # can you be more friendly?
    r"^can\s+you\s+bee?\s+more\s+{0}\s+\w+[.!?]*$",  # can you be more friendly please?
    r"^can\s+you\s+bee?\s+{0}[.!?]*$",  # can you be friendly?
    r"^can\s+you\s+bee?\s+{0}\s+\w+[.!?]*$",  # can you be friendly please?
]

# =============================================================================
# SCREENSHOT PATTERNS
# =============================================================================

# Patterns that REJECT screenshot requests (return [] / no tool call)
# "look/check twice/thrice/multiple times" and similar
SCREENSHOT_REJECT_PATTERNS = [
    r"^look\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^look\s+multiple\s+times[.!?]*$",
    r"^check\s+twice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+thrice(?:\s+at\s+this)?[.!?]*$",
    r"^check\s+multiple\s+times[.!?]*$",
]

# Pattern for "take X screenshot(s)" - captures X
SCREENSHOT_TAKE_X_PATTERN = r"^take\s+(\w+)\s+screenshots?[.!?]*$"

# Values of X that trigger a screenshot (singular)
SCREENSHOT_TRIGGER_QUANTITIES = {"one", "1", "once", "a"}

# Patterns that TRIGGER screenshot (return [{"name": "take_screenshot"}])
SCREENSHOT_TRIGGER_PATTERNS = [
    r"^take\s+screenshots?[.!?]*$",  # "take screenshot", "take screenshots"
    r"^screenshot\s+this[.!?]*$",  # "screenshot this"
    r"^sceenshot\s+this[.!?]*$",  # typo: "sceenshot this"
    r"^lok\s+at\s+this[.!?]*$",  # typo: "lok at this"
    r"^lock\s+at\s+this[.!?]*$",  # typo: "lock at this"
    r"^tkae\s+a\s+look[.!?]*$",  # typo: "tkae a look"
    r"^teak\s+a\s+look[.!?]*$",  # typo: "teak a look"
]

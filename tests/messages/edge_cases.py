"""Edge case scenarios: idioms, typos, meta questions, hypotheticals, abstract requests."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 21: Idioms & Metaphorical Language - False Triggers
    # Testing phrases with look/see that are NOT visual requests
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "idioms_and_metaphors",
        [
            ("I have been thinking about what you said earlier.", False),
            ("I see what you mean about the design.", False),
            ("Let me look into that and get back to you.", False),
            ("Look, I do not have time to argue about this.", False),
            ("See, that is exactly what I was trying to say.", False),
            ("We will see what happens with the project.", False),
            ("I will look into it tomorrow.", False),
            ("See you later.", False),
            ("Look alive, we have a deadline.", False),
            ("It remains to be seen if this will work.", False),
            ("I am seeing someone new, actually.", False),
            ("Let us see how this plays out.", False),
            ("Anyway, enough about that. Check this out.", True),
            ("This is what I was actually trying to show you.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 22: Typos & Formatting Variations - Should Still Trigger
    # Testing misspellings and weird formatting that should still work
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "typos_and_formatting",
        [
            ("I found something interesting online.", False),
            ("Lok at this.", True),
            ("Sorry, typo. I meant look at this.", True),
            ("Anyway, chekc this out.", True),
            ("Sceenshot this real quick.", True),
            ("Tkae a look.", True),
            ("LOOK AT THIS!", True),
            ("Why am I yelling? Sorry.", False),
            ("Look @ this though.", True),
            ("Check this out!", True),
            ("Oh my God, ths is crazy.", True),
            ("Loook at it.", True),
            ("Pek at this.", True),
            ("Anyway, here is what I wanted to show you.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 23: Meta Questions & Capability Checks - Not Visual Requests
    # Testing questions about the assistant's abilities vs actual requests
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "meta_questions_capability",
        [
            ("Hey, quick question.", False),
            ("Can you actually see my screen?", False),
            ("Like, do you have eyes or something?", False),
            ("How does the screenshot thing work, exactly?", False),
            ("I am just curious about your capabilities.", False),
            ("Can you see images in general?", False),
            ("Okay, cool, so you can see what I am looking at.", False),
            ("That is actually pretty useful.", False),
            ("Anyway, now that I know you can see.", False),
            ("Check this out.", True),
            ("Can you see that okay?", True),
            ("Is the quality good enough?", False),
            ("Let me know if you need me to zoom in.", False),
            ("Here is a closer look.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 24: Future & Hypothetical - Not Current Requests
    # Testing references to past or future showing, not present requests
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "future_and_hypothetical",
        [
            ("I have been meaning to show you something.", False),
            ("I will show you tomorrow when it is ready.", False),
            ("If I had a better camera, I would show you.", False),
            ("Remember that pic I showed you last week?", False),
            ("I might show you later if I have time.", False),
            ("I was going to show you, but I forgot.", False),
            ("Next time I will definitely show you.", False),
            ("I should have shown you earlier.", False),
            ("I wish I could show you what I mean.", False),
            ("Actually, wait. I can show you right now.", False),
            ("Here, let me pull it up.", False),
            ("Okay, here it is.", True),
            ("This is what I was talking about.", True),
            ("See what I mean now?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 25: Show Me Requests & Abstract Deictics - Generation vs Visual
    # Testing "show me" as generation request vs actual screen sharing
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "show_me_and_abstract",
        [
            ("Can you show me how to do this?", False),
            ("Show me the steps.", False),
            ("Show me an example.", False),
            ("That makes sense.", False),
            ("This is correct, I think.", False),
            ("Those were good times.", False),
            ("That is a good point, actually.", False),
            ("This implies we should change the approach.", False),
            ("Anyway, let me show you what I have so far.", False),
            ("Here.", True),
            ("See.", True),
            ("Right here.", True),
            ("This part specifically.", True),
            ("What do you think about that section?", True),
            ("The thing in the top right corner.", True),
            ("Check the bottom of the page.", True),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

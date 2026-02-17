"""Tech support and gaming scenarios."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Tech Support Nightmare - Phone Acting Weird
    # User has tech issues, showing error messages and weird behavior
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tech_support_nightmare",
        [
            ("My phone has been acting so weird lately.", False),
            ("The battery drains super fast even when I'm not using it.", False),
            ("And then this error keeps popping up.", True),
            ("I have no idea what it means.", False),
            ("Wait, hold on. Don't screenshot that.", False),
            ("Wrong screen. Let me go back.", False),
            ("Okay, here is the actual error.", True),
            ("It says something about storage, but I have 20 gigs free.", False),
            ("Look at my storage breakdown.", True),
            ("Why is Other taking up so much space?", False),
            ("I tried clearing the cache, but nothing changed.", False),
            ("Also, the Wi-Fi keeps disconnecting randomly.", False),
            ("See this notification I keep getting.", True),
            ("Should I just factory reset the whole thing?", False),
            ("Actually, wait. Look at this setting.", True),
            ("Is this supposed to be turned on?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Gaming Session - Build Help & Rage Moments
    # User playing a game, asking for build advice and sharing frustrating moments
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "gaming_session_chaos",
        [
            ("I have been playing this game for six hours and I am losing my mind.", False),
            ("This boss is actually broken. There is no way this is fair.", False),
            ("Look at his health bar. It barely moved.", True),
            ("I did like 500 damage and he has 50,000 HP.", False),
            ("Wait, don't look yet. I need to show you my build first.", False),
            ("Okay, here are my character stats.", True),
            ("Am I doing something wrong with the skill tree?", True),
            ("Someone on Reddit said to use fire damage, but I am using ice.", False),
            ("Look at the recommended build from this guide.", True),
            ("Mine looks completely different.", False),
            ("Okay, I respecced. Let me try the boss again.", False),
            ("Still getting destroyed. What the hell.", False),
            ("WAIT, I DID IT!", False),
            ("Look at the victory screen.", True),
            ("I am literally shaking right now.", False),
            ("That took me four hours. I need to lie down.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Code Debugging Nightmare - Error Messages & Stack Traces
    # User debugging code, sharing error messages and asking for help
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "code_debugging_nightmare",
        [
            ("I have been stuck on this bug for two days.", False),
            ("The app crashes every time I try to submit the form.", False),
            ("Take a look at the error trace.", True),
            ("I have no idea what 'undefined is not a function' means.", False),
            ("See this part of the stack trace.", True),
            ("It points to line 47.", False),
            ("Look at the code on that line.", True),
            ("I do not see anything wrong with it.", False),
            ("Wait, let me scroll up.", False),
            ("Actually, don't look yet. I want to check something.", False),
            ("Okay, never mind. False alarm.", False),
            ("Look at this variable here.", True),
            ("It should be an array, but it is coming back as null.", False),
            ("What about this function?", True),
            ("I think the issue might be in here.", True),
            ("Read the return statement.", True),
            ("Oh, I see it now. I forgot to return the value.", False),
        ],
    ),
]

__all__ = ["DATA"]

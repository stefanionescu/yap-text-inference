"""App usage scenarios: dating apps, shopping, food ordering, social media."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Dating App Dilemma - Swiping & Profile Feedback
    # User is on a dating app asking for help with matches and their own profile
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "dating_app_dilemma",
        [
            ("I'm on Hinge right now and I don't know what to do.", False),
            ("Like, there's this girl but her profile is giving mixed signals.", False),
            ("Peep this.", True),
            ("She's cute though, right?", True),
            ("Wait, her bio says she's into astrology... red flag or nah?", True),
            ("Ok, swipe right whatever lmao.", False),
            ("Oh wait, we matched!", False),
            ("What do I even say to her?", False),
            ("Check this opener I wrote.", True),
            ("Too cringe? Be honest.", False),
            ("Actually wait, look at her latest prompt response.", True),
            ("She mentioned she likes hiking, so maybe I should say something about that.", False),
            ("Ok, new opener, check it.", True),
            ("Sent it. Now we wait lol.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Online Shopping Spiral - Outfit Check & Price Comparison
    # User is shopping online, asking for opinions on clothes and deals
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "shopping_spiral",
        [
            ("Ok, so I need a fit for this party Saturday.", False),
            ("Been scrolling Shein for like 2 hours, help.", False),
            ("Is this too basic?", True),
            ("Wait, this one's actually fire.", True),
            ("But it's 80 bucks, that's kind of steep.", False),
            ("Let me check if it's cheaper on Amazon, hold up.", False),
            ("Found it for 45 bucks, look!", True),
            ("The reviews are mid though.", False),
            ("Someone said the material feels like plastic lmao.", False),
            ("Should I just cop the original or risk it?", False),
            ("Actually wait, there's a 20% code. Check if it works.", False),
            ("Nice, ok, 36 dollars, not bad.", False),
            ("Adding to cart right now.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Food Order Struggle - Menu Decisions & Delivery Tracking
    # User is trying to order food, comparing options, tracking delivery
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "food_order_struggle",
        [
            ("Starving, what should I order?", False),
            ("Can't decide between Thai and Indian.", False),
            ("This pad thai looks good though.", True),
            ("Wait, the reviews for this place are suspicious, look.", True),
            ("Ok, never mind, Indian it is.", False),
            ("This butter chicken combo worth 18 pounds?", True),
            ("Adding garlic naan, obviously.", False),
            ("The delivery fee is 7 green ones, that's robbery.", False),
            ("Whatever, I'm too hungry to care.", False),
            ("Ordered. ETA 45 mins.", False),
            ("Why is the driver going the opposite direction?", False),
            ("He literally passed my street, look at this map.", True),
            ("Food is here finally.", False),
            ("They forgot the naan. I'm actually going to cry.", False),
            ("Look at this sad order.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Late Night Doom Scroll - Random Content & Existential Thoughts
    # User is scrolling social media late at night, sharing random stuff
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "late_night_doom_scroll",
        [
            ("It's 2 AM and I'm still on TikTok, help.", False),
            ("My screen time is going to be astronomical this week.", False),
            ("Ok, but this video is actually hilarious, watch it.", True),
            ("Why is this so accurate though?", True),
            ("The comments are even better, look.", True),
            ("I should sleep, but the algorithm keeps feeding me bangers.", False),
            ("Ok, one more, then I'm done.", False),
            ("Lmao, this cat.", True),
            ("Wait, this is kind of sad actually.", True),
            ("Why does TikTok go from funny to existential so fast?", False),
            ("Anyway, look at this absolute unit of a dog.", True),
            ("I want one so bad.", False),
            ("Ok, for real though, goodnight.", False),
            ("Just kidding, one more, look at this sunset someone posted.", True),
            ("Ok, now goodnight, for real for real.", False),
        ],
    ),
]

__all__ = ["DATA"]

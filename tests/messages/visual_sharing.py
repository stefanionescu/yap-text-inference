"""Visual sharing scenarios: memes, house tours, pet photos, unboxing."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 16: Meme Sharing Spree - Deictic Heavy Reactions
    # User sharing memes and reacting with lots of "this" and "that" references
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "meme_sharing_spree",
        [
            ("I have been saving memes all week to show you.", False),
            ("This one is absolutely perfect.", True),
            ("That face in the corner kills me.", True),
            ("Wait, this next one is even better.", True),
            ("These two go together.", True),
            ("The timing on that is incredible.", False),
            ("This is literally me every morning.", True),
            ("And that is my roommate.", True),
            ("Those comments underneath are gold.", True),
            ("Someone replied with this.", True),
            ("That response is brutal.", True),
            ("Anyway, this whole thread is chaos.", True),
            ("I saved this one specifically for you.", True),
            ("That energy is unmatched.", False),
            ("This right here is the one.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 17: House Tour Walkthrough - Spatial Deictics & Visual Presentation
    # User showing their new place with lots of "here" and spatial references
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "house_tour_walkthrough",
        [
            ("I finally moved into my new place. Let me show you around.", False),
            ("Here is the living room.", True),
            ("That couch was such a good find.", True),
            ("These curtains came with the place.", True),
            ("Right here is where I set up my desk.", True),
            ("The lighting in this corner is perfect.", True),
            ("That plant over there is fake, but nobody can tell.", True),
            ("This is the kitchen.", True),
            ("Those cabinets are original from the 70s.", True),
            ("The previous owner left that weird painting.", True),
            ("I kind of like it, though.", False),
            ("Here is the bedroom.", True),
            ("This mattress was expensive, but worth it.", True),
            ("That closet is tiny, but it works.", True),
            ("And this is the view from my window.", True),
            ("Not bad, right?", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 19: Pet Photo Session - Deictic Animal Reactions
    # User sharing photos of their pet with lots of visual commentary
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "pet_photo_session",
        [
            ("Let me show you what my cat did today.", False),
            ("This is how I found her this morning.", True),
            ("That pose is ridiculous.", True),
            ("She was stuck like this for ten minutes.", True),
            ("These eyes are judging me so hard.", True),
            ("I tried to take a better photo, but this happened.", True),
            ("That blur is her running away.", True),
            ("Finally got a good one, though.", False),
            ("This is her favorite spot.", True),
            ("That blanket is officially hers now.", True),
            ("I bought her this new toy.", True),
            ("She hates it, obviously.", False),
            ("This face says it all.", True),
            ("Compare that to this one from last year.", True),
            ("She has gotten so big.", False),
            ("This angle makes her look chunky, though.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 20: Product Unboxing - Sequential Visual Presentation
    # User unboxing something they ordered with lots of "this is" and "here"
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "product_unboxing",
        [
            ("My package finally arrived. Let me open it.", False),
            ("This is the box it came in.", True),
            ("That damage on the corner is concerning.", True),
            ("Okay, here is what is inside.", True),
            ("This packaging is excessive.", True),
            ("So much plastic for no reason.", False),
            ("Here it is.", True),
            ("This is smaller than I expected.", True),
            ("That color is slightly different from the listing.", False),
            ("These instructions make no sense.", True),
            ("This diagram is useless.", True),
            ("Okay, I think I figured it out.", False),
            ("Here is the final setup.", True),
            ("That part is supposed to go there, right?", True),
            ("This does not look like the photo.", True),
            ("I might return it, honestly.", False),
            ("What do you think?", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

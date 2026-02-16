"""Non-visual scenarios: memories, comparing others, restaurant talk."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 27: Memory Lane - Past Experiences & Stories
    # User reminiscing about past events, not showing current content
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "memory_lane",
        [
            ("I have been thinking about that trip we took last summer.", False),
            ("The beach there was so beautiful.", False),
            ("That restaurant we found was incredible.", False),
            ("The sunset that night was perfect.", False),
            ("My favorite part was the boat ride.", False),
            ("Your idea to go hiking was great.", False),
            ("The view from the top was breathtaking.", False),
            ("Our hotel room was surprisingly nice.", False),
            ("The food at that little cafe was amazing.", False),
            ("I actually found some photos from that trip.", False),
            ("Let me show you.", False),
            ("Here is one from the beach.", True),
            ("This was the view I was talking about.", True),
            ("Remember this moment?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 28: Comparing Others - Possessives Without Visual
    # User comparing things belonging to others vs showing their own
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "comparing_others",
        [
            ("My roommate just got a new car.", False),
            ("Her car is way nicer than mine, honestly.", False),
            ("His apartment is twice the size of ours.", False),
            ("Their kitchen has an island and everything.", False),
            ("My sister's wedding was so fancy.", False),
            ("The venue she picked was gorgeous.", False),
            ("His speech made everyone cry.", False),
            ("Her dress was stunning, apparently.", False),
            ("I could never afford something like that.", False),
            ("Anyway, I am looking at cars now too.", False),
            ("Check this one out.", True),
            ("This is in my budget, at least.", True),
            ("The interior looks decent.", False),
            ("What do you think compared to hers?", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 30: Restaurant & Food Chat - Past vs Present
    # User talking about food experiences vs showing current food
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "restaurant_food_chat",
        [
            ("That new Italian place downtown is overrated.", False),
            ("The pasta there was so bland.", False),
            ("My friend's recommendation was way better.", False),
            ("His favorite spot has the best tacos.", False),
            ("Their portions are huge for the price.", False),
            ("The service at that cafe was terrible.", False),
            ("Our waiter forgot our order twice.", False),
            ("The ambiance was nice, though.", False),
            ("My usual order there is the salmon.", False),
            ("Anyway, I am at a new place right now.", False),
            ("This menu looks interesting.", True),
            ("See the prices, though.", True),
            ("This dish sounds good.", True),
            ("The reviews for this place are decent.", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

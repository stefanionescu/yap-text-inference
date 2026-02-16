"""Planning and creative scenarios: studying, cooking, travel, design."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Study Session Struggle - Homework Help & Confused About Notes
    # User studying for exam, needs help reading notes and solving problems
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "study_session_struggle",
        [
            ("I have a chemistry exam tomorrow and I am so behind.", False),
            ("I have been trying to understand this chapter for three hours.", False),
            ("Can you read this section from my textbook?", True),
            ("I wrote notes, but I cannot read my own handwriting.", False),
            ("Look at this mess.", True),
            ("Is that supposed to be an H or a K?", True),
            ("Anyway, I am stuck on this practice problem.", False),
            ("See the question here.", True),
            ("I keep getting a different answer than the solution.", False),
            ("Let me show you my work.", False),
            ("Where did I go wrong?", True),
            ("Oh wait, I think I see it now.", False),
            ("I used the wrong formula.", False),
            ("Let me try again, hold on.", False),
            ("Okay, check this.", True),
            ("Is that right now?", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Cooking Disaster - Recipe Following & Troubleshooting
    # User trying to follow a recipe, things going wrong, asking for help
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "cooking_disaster",
        [
            ("I am trying to make this pasta carbonara I found online.", False),
            ("The recipe says to mix the eggs while the pasta is hot.", False),
            ("But I am worried about scrambling them.", False),
            ("Can you check the recipe? I have it on my screen.", True),
            ("Wait, the sauce looks weird.", False),
            ("Is it supposed to look like this?", True),
            ("I think I messed something up.", False),
            ("The comments say people had issues with curdling.", False),
            ("Look at the top comment.", True),
            ("They say to let the pasta cool first.", False),
            ("Okay, I am starting over.", False),
            ("Round two, let's go.", False),
            ("Okay, this looks better.", True),
            ("Still a bit chunky, though.", False),
            ("Whatever, close enough. I am hungry.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Travel Planning Chaos - Comparing Options & Booking Issues
    # User planning a trip, comparing flights and hotels, dealing with booking problems
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "travel_planning_chaos",
        [
            ("I am trying to book a trip to Barcelona for next month.", False),
            ("The flight prices are all over the place.", False),
            ("This one is 400 dollars, but has two layovers.", True),
            ("And this one is direct, but costs 700.", True),
            ("Which one would you pick?", False),
            ("I hate layovers, but I also hate spending money.", False),
            ("Okay, let me look at hotels now.", False),
            ("Found this place near the beach.", True),
            ("The reviews look good.", True),
            ("Wait, someone said there were bedbugs.", False),
            ("Let me find that review, hold on.", False),
            ("See this one.", True),
            ("That is concerning.", True),
            ("Actually, never mind. Don't look at that one.", False),
            ("I found a better option.", False),
            ("Check this hotel instead.", True),
            ("It is a bit more expensive, but looks way nicer.", False),
            ("The photos are probably edited, though.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Design Feedback Loop - Logo Iterations & Client Revisions
    # User working on design project, showing iterations and handling feedback
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "design_feedback_loop",
        [
            ("I have been working on this logo for a client all week.", False),
            ("They keep asking for revisions and I am losing my mind.", False),
            ("Here is the original design I sent them.", True),
            ("I thought it looked great.", False),
            ("But they wanted more color.", False),
            ("So I made this version.", True),
            ("Then they said it was too busy.", False),
            ("Here is what I came up with after that.", True),
            ("Now they want the icon bigger.", False),
            ("I see what they mean, but I disagree.", False),
            ("Look at the proportions.", True),
            ("If I make it bigger, it will look unbalanced.", False),
            ("Anyway, here is the latest revision.", True),
            ("I honestly cannot tell the difference anymore.", False),
            ("Wait, they just sent another email.", False),
            ("Don't look at the logo yet.", False),
            ("Let me read what they want now.", False),
            ("Okay, they want to go back to version two.", False),
            ("Look at it.", True),
            ("I actually cannot believe this.", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

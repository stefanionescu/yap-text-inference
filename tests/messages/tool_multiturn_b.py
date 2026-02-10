"""Context-dependent and scenario-based multi-turn prompts."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ── CONTEXT DEPENDENT: SAME PHRASE, DIFFERENT OUTCOME ────────────────────────
    (
        "context_dependent_right_or_wrong_text",
        [
            ("My friend and I argued about rent, they're always slacking", False),
            ("Am I in the right here?", False),
            ("Will have to give him an ultimatum", False),
        ],
    ),
    (
        "context_dependent_right_or_wrong_visual",
        [
            ("This convo is intense", False),
            ("Look at what he said", True),
            ("Am I in the right here?", True),  # Referring to the visible chat
        ],
    ),
    (
        "context_dependent_what_do_you_think_text",
        [
            ("I have a theory about the universe.", False),
            ("It's all a simulation.", False),
            ("What do you think?", False),
        ],
    ),
    (
        "context_dependent_what_do_you_think_visual",
        [
            ("I made a new logo design.", False),
            ("check this out", True),
            ("What do you think?", True),  # Evaluation of visual
        ],
    ),
    (
        "context_dependent_is_it_good_text",
        [
            ("I saw a movie last night.", False),
            ("It was the new Marvel one.", False),
            ("Is it good?", False),
            ("I'm thinking of the iPhone 15.", False),
            ("Is it good?", False),
        ],
    ),
    (
        "context_dependent_is_it_good_visual",
        [
            ("I'm working on my cable management.", False),
            ("look at this mess", True),
            ("Is it good?", True),  # sarcastic or genuine visual check
        ],
    ),
    (
        "context_dependent_feedback_text",
        [
            ("I need feedback on my life choices.", False),
            ("I quit my job to be a poet.", False),
            ("Any thoughts?", False),
        ],
    ),
    (
        "context_dependent_feedback_visual",
        [
            ("I need feedback on my dating profile.", False),
            ("see this bio", True),
            ("Any thoughts?", True),
        ],
    ),
    (
        "context_dependent_help_text",
        [
            ("I'm stuck in a rut.", False),
            ("Everything feels gray.", False),
            ("Can you help me?", False),
        ],
    ),
    (
        "context_dependent_help_visual",
        [
            ("I'm stuck in this game level.", False),
            ("Look at this puzzle.", True),
            ("Can you help me?", True),
        ],
    ),
    # ── SCENARIO: Navigation/Guidance ─────────────────────────────────────────────
    (
        "navigation_flow",
        [
            ("I'm lost in this menu.", False),
            ("Where do I go?", False),
            ("Look at the options", True),
            ("Click the first one", False),
            ("Now what?", False),
            ("Is this the right page?", True),
        ],
    ),
    # ── SCENARIO: Physical Object Presentation ────────────────────────────────────
    (
        "physical_object_showcase",
        [
            ("I bought a new watch.", False),
            ("It's a Seiko.", False),
            ("Hold on, let me put it under the camera.", False),  # Setup action
            ("Can you see the dial?", True),
            ("Is it real?", False),
        ],
    ),
    # ── MULTI-TURN: Negation Patterns ────────────────────────────────────────────────
    (
        "negation_cancel_sequence",
        [
            ("Look at this", True),
            ("Actually nevermind, don't look", False),
            ("Just kidding, look now", True),
        ],
    ),
    (
        "negation_hesitation",
        [
            ("I want to show you something", False),
            ("Wait, don't look yet", False),
            ("Okay now you can look", True),
        ],
    ),
    (
        "negation_correction",
        [
            ("Check this out", True),
            ("Actually cancel that, don't screenshot", False),
            ("Nevermind, look at this instead", True),
        ],
    ),
    (
        "negation_context_switch",
        [
            ("Look at this dress", True),
            ("Actually don't look, I changed my mind", False),
            ("Let me show you something else", False),
            ("Here, look at this one", True),
        ],
    ),
    (
        "negation_embarrassment",
        [
            ("I wanna show you something", False),
            ("Actually don't look, it's embarrassing", False),
            ("Okay fine, look at it", True),
        ],
    ),
    (
        "negation_repeated_cancel",
        [
            ("I'm about to show you something wild", False),
            ("Okay here it is, check this out", True),
            ("Wait no, don't look at that", False),
            ("That was the wrong thing", False),
            ("Okay THIS is what I wanted to show you", True),
            ("No wait, don't look at this one either", False),
            ("Ugh let me find the right one", False),
            ("Okay finally, look at this", True),
        ],
    ),
    (
        "negation_privacy_concern",
        [
            ("I was gonna show you this conversation I had", False),
            ("Actually don't look, there's personal info in there", False),
            ("Let me blur some stuff out first", False),
            ("Okay now you can look at it", True),
            ("Does that message seem passive aggressive to you?", True),
        ],
    ),
    (
        "negation_wrong_screen",
        [
            ("Hold on let me share my screen", False),
            ("Wait don't look yet, that's the wrong window", False),
            ("I need to switch to the right tab", False),
            ("Don't screenshot that, it's not what I meant to show", False),
            ("Okay now look at this", True),
        ],
    ),
    (
        "negation_not_ready",
        [
            ("I'm working on this design and want your feedback", False),
            ("Don't look at it yet though, it's not done", False),
            ("I'm still tweaking some things", False),
            ("Almost ready, don't peek", False),
            ("Okay NOW you can look at it", True),
            ("What do you think so far?", False),
        ],
    ),
    (
        "negation_teasing",
        [
            ("I have something amazing to show you", False),
            ("But don't look yet", False),
            ("Are you ready?", False),
            ("Okay don't look, I'm building suspense", False),
            ("Alright fine, check this out", True),
        ],
    ),
    # ── MULTI-TURN: Quantity Trap Patterns ────────────────────────────────────────────
    (
        "quantity_escalation",
        [
            ("Check this out", True),
            ("Cool right?", True),
            ("Now take 3 more screenshots of the details", False),
            ("And 2 more of the corners", False),
        ],
    ),
    (
        "quantity_request_sequence",
        [
            ("Look at this car", True),
            ("I need 4 screenshots of different angles", False),
            ("Can you take 5 more?", False),
        ],
    ),
    (
        "quantity_misunderstanding",
        [
            ("See this?", True),
            ("Take screenshots of everything", False),
            ("I mean just one screenshot", True),
        ],
    ),
    (
        "quantity_clarification",
        [
            ("Check this out", True),
            ("Take 6 screenshots", False),
            ("Wait, I meant just one", True),
        ],
    ),
    # ── MULTI-TURN: Positive Triggers That Might Be Missed ───────────────────────────
    (
        "debugging_context_buildup",
        [
            ("I have a bug in my code", False),
            ("It's in the main function", False),
            ("Take a look at the error trace", True),
            ("What about this line?", True),
            ("And this one too?", True),
        ],
    ),
    (
        "narrative_to_visual",
        [
            ("I was walking downtown", False),
            ("Saw something crazy", False),
            ("Look at it", True),
            ("See what I mean?", True),
        ],
    ),
    (
        "contextual_reference",
        [
            ("I'm working on a project", False),
            ("The design is almost done", False),
            ("Check this out", True),
            ("What do you think?", True),
        ],
    ),
    (
        "gradual_reveal",
        [
            ("I have something to show you", False),
            ("It's really cool", False),
            ("Ready?", False),
            ("Look at this", True),
        ],
    ),
    (
        "error_diagnosis_flow",
        [
            ("My app crashed", False),
            ("The logs show something weird", False),
            ("Take a look at the error trace", True),
            ("See this part?", True),
            ("What about this line?", True),
        ],
    ),
    (
        "comparison_request",
        [
            ("I'm choosing between two options", False),
            ("This one first", True),
            ("Now this one", True),
            ("Which do you prefer?", False),
        ],
    ),
    (
        "technical_support",
        [
            ("I'm having trouble with my setup", False),
            ("The config looks wrong", False),
            ("Check this out", True),
            ("See the problem?", True),
        ],
    ),
    (
        "visual_feedback_sequence",
        [
            ("I made something", False),
            ("Want to see?", False),
            ("Look at it", True),
            ("What do you think?", True),
        ],
    ),
    (
        "code_review_request",
        [
            ("I wrote some code", False),
            ("Not sure if it's right", False),
            ("Take a look at this", True),
            ("What about this function?", True),
        ],
    ),
    (
        "design_feedback",
        [
            ("I'm working on a logo", False),
            ("Almost done", False),
            ("Check this out", True),
            ("See what I mean?", True),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

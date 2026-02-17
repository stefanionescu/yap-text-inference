"""Social drama scenarios: online drama, gossip, work complaints."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 18: Online Drama Recap - Implicit Visual References & Commentary
    # User explaining internet drama with lots of implicit "look at what happened"
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "online_drama_recap",
        [
            ("Okay, so this influencer got cancelled yesterday.", False),
            ("This tweet started it all.", True),
            ("That ratio is insane.", True),
            ("Then she posted this response.", True),
            ("Which made it worse, obviously.", False),
            ("These replies are brutal.", True),
            ("Someone dug up this old post.", True),
            ("That aged terribly.", True),
            ("Her subscriber count is dropping.", False),
            ("This graph shows the decline.", True),
            ("That dip right there is when the video dropped.", True),
            ("Now this other creator made a response.", False),
            ("This part is where it gets spicy.", True),
            ("Those screenshots are damning.", True),
            ("I cannot believe she said that.", False),
            ("Anyway, this whole situation is a mess.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 26: Gossip Session - Talking About Others (Not Present)
    # User gossiping about friends/people using possessives and past tense
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "gossip_session",
        [
            ("Okay, so I need to tell you about my coworker.", False),
            ("Her attitude lately has been unbearable.", False),
            ("She thinks she is better than everyone else.", False),
            ("His girlfriend told me the whole story.", False),
            ("Their relationship is honestly a mess.", False),
            ("The drama at that party was insane.", False),
            ("My friend Sarah's boyfriend is so annoying.", False),
            ("His jokes are never funny, but he thinks they are.", False),
            ("Anyway, she sent me this message about it.", False),
            ("Look at what she said.", True),
            ("Her response was wild, right?", False),
            ("Then he sent her this.", True),
            ("His excuse was so lame.", False),
            ("Their whole friend group is taking sides now.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 29: Work Complaints - Talking About Colleagues
    # User venting about work without showing vs showing evidence
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "work_complaints",
        [
            ("My boss is driving me crazy lately.", False),
            ("His expectations are completely unrealistic.", False),
            ("Her management style is so passive-aggressive.", False),
            ("Their department always gets the good projects.", False),
            ("My coworker's work ethic is nonexistent.", False),
            ("She takes credit for everyone else's ideas.", False),
            ("The meeting yesterday was a disaster.", False),
            ("His presentation was embarrassing, honestly.", False),
            ("Her feedback on my project was so harsh.", False),
            ("Their timeline makes no sense.", False),
            ("Anyway, he sent this email today.", True),
            ("Look at the tone.", True),
            ("This part is what got me.", True),
            ("Am I overreacting, or is this passive-aggressive?", True),
        ],
    ),
]

__all__ = ["DATA"]

"""Life scenarios: group chat drama, job hunting, apartment search, fitness."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Group Chat Drama - Screenshots & Receipts
    # User is dealing with friend drama and showing messages as evidence
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "group_chat_drama",
        [
            ("Dude, you won't believe what just happened in the group chat.", False),
            ("So basically Emma and Jake are fighting AGAIN.", False),
            ("Look at what she said.", True),
            ("And then HE said this back.", True),
            ("I'm literally just watching this unfold eating popcorn.", False),
            ("Wait, it gets worse. Look.", True),
            ("She just brought up something from like 3 months ago.", False),
            ("Honestly, I kind of agree with Emma here, but don't tell anyone.", False),
            ("Oh my God, Jake just left the chat.", False),
            ("WAIT, HE MADE A NEW ONE WITHOUT HER.", False),
            ("See this.", True),
            ("Should I add her back or stay neutral?", False),
            ("This is so messy, I can't.", False),
            ("She just texted me privately. Look.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Job Hunt Anxiety - Resume Review & LinkedIn Stalking
    # User is applying for jobs, wants feedback on resume and comparing profiles
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "job_hunt_anxiety",
        [
            ("I have been applying to jobs for three weeks and nothing.", False),
            ("Maybe my resume is the problem.", False),
            ("Can you take a look at it?", True),
            ("I feel like the format is outdated.", False),
            ("Wait, actually don't look yet.", False),
            ("Let me fix this one section first.", False),
            ("Okay, now you can look.", True),
            ("Is the experience section too long?", True),
            ("I saw this guy on LinkedIn who got hired at the same company.", False),
            ("His profile is insane. Look at this.", True),
            ("He has like 500 endorsements for Excel.", False),
            ("Should I add more skills to mine?", False),
            ("Check out my skills section.", True),
            ("Also, thoughts on this cover letter I wrote?", True),
            ("I think it sounds too desperate, honestly.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Apartment Hunt Despair - Listings & Roommate Drama
    # User is looking for apartments, dealing with bad listings and roommate issues
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "apartment_hunt_despair",
        [
            ("Apartment hunting in this city is actually impossible.", False),
            ("Everything decent is like 2000 a month minimum.", False),
            ("Found this place that seems okay, though.", True),
            ("The photos look kind of staged, but whatever.", False),
            ("Wait, no, don't look at that one actually.", False),
            ("I just saw the reviews and apparently there are roaches.", False),
            ("Let me find the other one I saved.", False),
            ("Okay, check this listing out.", True),
            ("It is a bit further from my work, but the price is right.", False),
            ("The kitchen looks tiny, though.", False),
            ("Also, my current roommate is driving me insane.", False),
            ("She left this passive aggressive note on the fridge.", True),
            ("Look at what she wrote.", True),
            ("Am I crazy or is this ridiculous?", False),
            ("Anyway, I need to get out of here as soon as possible.", False),
            ("What do you think of the apartment, though?", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Fitness Journey - Progress Pics & Workout Plans
    # User tracking fitness progress, comparing before/after, checking workout routines
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "fitness_journey_progress",
        [
            ("Okay, so I have been going to the gym for two months now.", False),
            ("I think I am finally starting to see some progress.", False),
            ("Here is my progress pic from today.", True),
            ("Compared to where I started.", False),
            ("The lighting is kind of bad, but you can still tell, right?", False),
            ("My trainer sent me a new workout plan.", False),
            ("Look at this routine.", True),
            ("Is this too many leg days?", True),
            ("I already can barely walk after squats.", False),
            ("Also, I have been tracking my calories.", False),
            ("Actually, never mind, don't look at that.", False),
            ("I had pizza yesterday and it ruined everything.", False),
            ("But check out this meal prep I did.", True),
            ("Pretty proud of it, honestly.", False),
            ("Do you think I should add more protein?", False),
            ("Here is the nutrition breakdown.", True),
        ],
    ),
]

__all__ = ["DATA"]

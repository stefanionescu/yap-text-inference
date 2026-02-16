"""Health and wellness scenarios: step counts, sleep tracking, calorie counting, screen time, fitness stats."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Step Count Competition - Trying to beat a friend's daily steps
    # User is in a step count challenge and obsessively checking the leaderboard
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "step_count_competition",
        [
            ("Bro, I'm literally speed walking around my apartment right now trying to beat Marcus.", False),
            ("Look at the leaderboard right now, he's only 400 steps ahead.", True),
            ("I've been walking in circles for like 20 minutes. This is pathetic.", False),
            ("Not going to lie, I might just shake my phone at this point. I don't even care.", False),
            ("WAIT, check this out, I just passed him.", True),
            ("I swear to God, if he goes for a run tonight I'm going to lose it.", False),
            ("This number right here is all that matters right now. 12,847 steps baby.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Sleep Tracker Shame - Embarrassingly bad sleep score
    # User woke up feeling terrible and the sleep data confirms it
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "sleep_tracker_shame",
        [
            ("I already know I slept like garbage last night. I didn't need an app to tell me that.", False),
            ("Look at this sleep score though, that's genuinely embarrassing.", True),
            ("47 out of 100, like how is that even possible.", False),
            ("I was tossing and turning til like 3am thinking about dumb stuff.", False),
            ("To be honest, I need to stop looking at my phone before bed, but that's never going to happen.", False),
            ("This deep sleep number is concerning, for real. Like 12 minutes?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Calorie Counter Shock - That meal was way more than expected
    # User scanned a meal and is horrified by the calorie count
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "calorie_counter_shock",
        [
            ("Okay so I just scanned my Chipotle bowl into MyFitnessPal and I need to sit down.", False),
            ("See this number right here. That can't be right.", True),
            ("There's no way a burrito bowl is 1200 calories, like WHAT.", False),
            ("I thought I was being healthy getting a bowl instead of a burrito lmao.", False),
            ("Check this breakdown though, the guac alone is insane.", True),
            ("I've been eating this three times a week thinking I was on a diet, bruh.", False),
            ("Look at my daily total now, it's over by like 600 calories and it's only 2pm.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Screen Time Report - Weekly usage is embarrassing
    # User got the weekly screen time notification and is in denial
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "screen_time_weekly_shock",
        [
            ("My phone just hit me with the weekly screen time report and I feel attacked.", False),
            ("Look at this. Seven hours and 43 minutes DAILY AVERAGE.", True),
            ("The TikTok number is honestly criminal, like see this breakdown.", True),
            ("I spent more time on my phone than I did sleeping apparently.", False),
            ("And it's up 23 percent from last week somehow? How is that even possible?", False),
            ("This is genuinely making me reconsider my life choices, not going to lie.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Running App PR - Just hit a personal best on a 5K
    # User finished a run and is hyped about the time showing on the app
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "running_app_personal_best",
        [
            ("YOOOOO I JUST HIT A PR ON MY 5K I'M SCREAMING.", False),
            ("Look at this time. 23:41, that's almost two minutes faster than last month.", True),
            ("I thought I was going to die at mile 2 but I pushed through.", False),
            ("See this pace chart though, I totally died in the middle and then recovered.", True),
            ("My legs are literally shaking right now, I can barely stand.", False),
            ("My friend who runs marathons is going to say it's not impressive but I don't care.", False),
            ("Look at the elevation map too, I did this on hills, not flat ground.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Heart Rate Zone Confusion - Numbers look weird during workout
    # User is mid-workout and confused by heart rate data
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "heart_rate_zone_confusion",
        [
            ("Okay so I was doing a pretty chill bike ride and my watch started freaking out.", False),
            ("Is this heart rate normal? It says 187 but I feel totally fine.", True),
            ("I don't know if the sensor is broken or if I'm secretly about to pass out.", False),
            ("I googled it and apparently my max should be like 195, so that's kind of close.", False),
            ("Lowkey scared now, to be honest. Maybe I should go to a doctor.", False),
            ("Check this graph though, it spiked out of nowhere for no reason.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Water Intake Tracker - Not drinking enough and feeling guilty
    # User checks water tracker and realizes they've barely had any water
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "water_intake_guilt",
        [
            ("I downloaded a water tracker app because I literally never drink water.", False),
            ("It's 4pm and look at how empty this progress bar is. That's so sad.", True),
            ("I've had like two cups total and four coffees lmao.", False),
            ("My body is running on caffeine and vibes at this point.", False),
            ("This notification keeps popping up telling me to drink water and I keep ignoring it.", False),
            ("See this weekly chart though, not a single day did I hit the goal.", True),
            ("I think I might just be a raisin at this point, for real.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Apple Watch Rings - Desperate to close all three rings
    # User is obsessed with closing activity rings before midnight
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "watch_ring_closing_obsession",
        [
            ("It's 11:30pm and I still haven't closed my move ring. I'm panicking.", False),
            ("Look at how close I am though, it's literally 96 percent.", True),
            ("Going to do jumping jacks in my room until it closes. I don't care.", False),
            ("I have a 47 day streak going, I CANNOT break it tonight.", False),
            ("My roommate thinks I'm insane walking around the apartment at midnight.", False),
            ("THIS JUST CLOSED, CHECK IT. All three rings, baby, let's gooo.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Body Composition Scan - Results from the gym's InBody machine
    # User did a body scan at the gym and is analyzing the results
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "body_composition_scan",
        [
            ("So the gym got one of those InBody scanner things and I tried it today.", False),
            ("Look at these results, I'm trying to figure out what half of this means.", True),
            ("My skeletal muscle mass is apparently above average, so that's cool I guess.", False),
            ("But see this body fat percentage right here. That's higher than I expected, not going to lie.", True),
            ("The trainer said the visceral fat score is what's important though.", False),
            ("How is this accurate though? I feel like it changes every time you do it.", True),
            ("Going to do another one in three months and see if anything changes.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Meditation App Streak - Trying not to lose the streak
    # User is maintaining a meditation streak but barely actually meditating
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "meditation_app_streak",
        [
            ("I have a 90 day meditation streak on Headspace but I'm lowkey a fraud.", False),
            ("Half the time I just press play and scroll through Twitter lmao.", False),
            ("See this stats page though, it looks so impressive.", True),
            ("90 days and like 42 hours of total meditation time apparently.", False),
            ("My therapist would be proud if she knew, but also disappointed if she knew the truth.", False),
            ("This mindfulness score is hilarious considering I wasn't even paying attention.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Workout Form Check - Recording exercise for feedback
    # User recorded themselves doing a lift and wants to check their form
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "workout_form_check_video",
        [
            ("I've been doing deadlifts for a month and I don't know if my form is right.", False),
            ("Check this video I recorded at the gym today.", True),
            ("Does my back look rounded to you, because someone said it looked off?", False),
            ("Look at this angle right here when I start the pull.", True),
            ("I watched a bunch of YouTube videos but I still can't tell if I'm doing it right.", False),
            ("Also see this part where I lock out at the top, does that look okay?", True),
            ("I'm scared of hurting myself so I've been keeping the weight pretty low.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Cycle Tracker Predictions - App predictions vs reality
    # User is comparing the tracker's predictions with how they actually feel
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "cycle_tracker_predictions",
        [
            ("My cycle tracker said my period was supposed to come three days ago and nothing.", False),
            ("Look at these predictions, they are never right, I swear to God.", True),
            ("Last month it was off by like five days too. This app is useless.", False),
            ("This fertile window thing is so wrong based on everything I've tracked.", True),
            ("My friend swears by Flo but honestly I think they all just guess.", False),
            ("See this chart though, the pattern is literally all over the place.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Strava Segment Competition - Fighting for a local KOM/QOM
    # User is competing on Strava segments and obsessing over leaderboard
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "strava_segment_competition",
        [
            ("Dude, I'm so close to getting the KOM on the hill segment near my house.", False),
            ("Look at this leaderboard, I'm literally 4 seconds behind first place.", True),
            ("I've been riding that hill every single day this week trying to beat it.", False),
            (
                "The guy in first probably has a carbon bike that costs like 8 grand and I'm on an aluminum beater.",
                False,
            ),
            ("Check this power curve from today's attempt, I was going all out.", True),
            ("My heart was about to explode at the top, but it's so close I can't give up.", False),
            ("See this comparison between my best run and his. There's no way I can't close that gap.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: MyFitnessPal Logging Struggle - Trying to track meals honestly
    # User is attempting to log food accurately and getting frustrated
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "mfp_food_diary_struggle",
        [
            ("Logging food in MyFitnessPal is honestly a part time job. I can't do this.", False),
            ("I spent 10 minutes trying to find the exact brand of yogurt I ate.", False),
            ("And there's like 47 entries for greek yogurt. How do I know which one is right?", False),
            ("Look at what it says for a homemade smoothie, that's got to be wrong.", True),
            ("Who is out here eating exactly one tablespoon of peanut butter, be so for real.", False),
            ("This macro breakdown for today looks insane. Way too much sugar apparently.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Weekly Health Summary - Comparing this week vs last week
    # User is reviewing the weekly health dashboard and comparing trends
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "weekly_health_summary_comparison",
        [
            ("Okay so it's Sunday and I'm doing my weekly health check in.", False),
            ("Look at this summary though. Everything went down from last week.", True),
            ("Steps down 22 percent, sleep score down, and resting heart rate went up. Great.", False),
            ("To be honest, I was traveling for work so I kind of expected it to be bad.", False),
            ("But see this comparison side by side, it's actually depressing.", True),
            (
                "The only thing that improved was my mindful minutes and that's because I passed out during a session lmao.",
                False,
            ),
            ("These stats are making me want to just not look at them honestly.", True),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

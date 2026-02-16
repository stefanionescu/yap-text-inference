"""Daily utility scenarios: weather checks, calendar conflicts, alarms, notes, storage, battery health."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Weather App Obsession - Outfit Planning Paralysis
    # User keeps refreshing the weather app trying to figure out what to wear
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "weather_app_outfit_panic",
        [
            ("I've checked the weather like nine times today and it keeps changing on me.", False),
            ("Like, do I bring a jacket or not, because this forecast is all over the place? Look.", True),
            ("Is this even accurate though? It said 72 this morning and now it's showing 58.", False),
            ("Not going to lie, weather apps are so unreliable. I don't even know why I bother.", False),
            ("Wait, ok, this hourly breakdown actually makes more sense. Look at the evening temps.", True),
            ("I'm just going to layer up and hope for the best, honestly.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Calendar Double-Booking Panic - Overlapping Events
    # User realizes they scheduled two things at the same time and is spiraling
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "calendar_double_book",
        [
            ("Bruh, I just realized I have two things at 3pm tomorrow. I'm cooked.", False),
            ("This schedule is actually insane. How did I let this happen?", False),
            ("Like, I told my dentist I'd be there and I also told my manager we'd do a one on one.", False),
            ("Is there any overlap or am I tripping? Look at the times.", True),
            ("The dentist is 3 to 3:45 and the meeting starts at 3:30, so yeah, I'm screwed.", False),
            ("I'm going to have to reschedule one of them. This is so annoying.", False),
            ("Wait, does this say the meeting got moved to 4? Oh my God, saved.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Alarm Setup Paranoia - Five Alarms for One Event
    # User is setting multiple alarms because they cannot afford to oversleep
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "alarm_setup_paranoia",
        [
            ("Ok, so I have a flight at 6am, which means I need to be up by like 3:30.", False),
            ("Setting five alarms right now because I literally cannot miss this flight.", False),
            ("3:30, 3:35, 3:40, 3:45, and a nuclear one at 3:50 with the loudest tone.", False),
            ("Wait, does this alarm say PM instead of AM? That would've ruined me.", True),
            ("Ok, fixed it. Also turned off the weekend-only repeat on this one, see?", True),
            ("If I sleep through all five of these, I genuinely deserve to miss the flight, to be honest.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Drunk Notes Discovery - Mysterious Messages From Past Self
    # User finds chaotic notes they wrote while drunk and tries to decode them
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "drunk_notes_discovery",
        [
            ("So I just opened my notes app and apparently drunk me had a LOT to say last night.", False),
            ("Look at this absolute masterpiece I wrote at 2am.", True),
            ("It just says 'the frogs know everything ask them.' WHAT DOES THAT MEAN?", False),
            ("And then this one is a full business plan for edible shoelaces? Look.", True),
            ("Honestly, the shoelace thing might have potential, not going to lie.", False),
            ("Wait, there's more. Oh my God, this one has a drawing too. See this?", True),
            ("I need to stop unlocking my phone when I'm drunk, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Storage Full Crisis - Cannot Take Photos
    # User's phone is out of storage and they're losing it about not being able to take pics
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "storage_full_crisis",
        [
            ("My phone literally just told me I can't take photos because storage is full. I'm going to cry.", False),
            ("I have like 14000 photos and most of them are probably blurry screenshots of nothing.", False),
            ("Look at this storage breakdown though. It's insane.", True),
            ("Why is 'other' taking up 23 gigs? WHAT IS OTHER?", True),
            ("Look, I deleted like 200 photos and this still says 0.3 gigs freed. That can't be right.", True),
            ("Honestly, I just need a new phone at this point. I'm not deleting anything else.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Battery Health Anxiety - Watching the Percentage Drop
    # User is obsessing over battery health stats and degradation
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "battery_health_anxiety",
        [
            ("Ok, so I just checked my battery health and I think my phone is dying.", False),
            ("This battery health percentage is actually depressing. Look at it.", True),
            ("87 percent maximum capacity and I got this phone like a year ago. That can't be normal.", False),
            ("I read somewhere you're not supposed to charge overnight, but who actually does that?", False),
            ("Is this cycle count bad or am I overthinking it? Be honest.", True),
            ("I might start carrying a portable charger everywhere because this drain is unreal.", False),
            ("Wait, what does this setting do? Does optimized charging actually help?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Calculator Bill Split Chaos - Splitting Dinner Unevenly
    # User is trying to split a complicated restaurant bill with friends
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "calculator_bill_split",
        [
            ("Trying to split this dinner bill and it's giving me a headache. Nobody ordered the same thing.", False),
            (
                "Ok, so Jake had the steak which was 34 and Emma had a salad for 12. That's already not fair to split evenly.",
                False,
            ),
            ("Wait, look at this total though. Does that include tip or not?", True),
            ("See, this is what the calculator says. Each person owes 28.73 before tip.", True),
            ("This breakdown right here shows tax was already added, see?", True),
            ("Whatever, I'm just going to Venmo request everyone 35 flat and call it a day.", False),
            ("If anyone complains, they can do the math themselves lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Reminders Overwhelm - Too Many To-Do Items
    # User opens their reminders and realizes they've been ignoring everything
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reminders_overwhelm",
        [
            ("Just opened my reminders app and I have 47 overdue tasks. I am not ok.", False),
            ("Look at these dates. Some of these are from literal months ago. This is embarrassing.", True),
            ("This one says 'call dentist' from November. Bruh, it's February.", True),
            ("And look at this one. I set a reminder to 'be better.' Like, what does that even mean?", True),
            ("I'm just going to clear all of them and start fresh, to be honest. Life's too short.", False),
            ("Wait, no, some of these are actually important. Never mind.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Weather Radar Outdoor Plans - BBQ or Bust
    # User is checking the radar obsessively before an outdoor event
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "weather_radar_bbq",
        [
            ("We're supposed to do a BBQ tomorrow and I've been staring at the radar all day.", False),
            ("Look at this radar loop though. That green blob is heading right for us.", True),
            ("It says 60 percent chance of rain between 2 and 5, which is literally when we planned it.", False),
            ("Should we just move it inside or risk it? Because last time we moved it and it didn't even rain.", False),
            ("Wait, this updated forecast actually looks better. See, the afternoon cleared up.", True),
            ("Ok, we're keeping it outside. I'm manifesting good weather right now.", False),
            ("If it rains, I'm blaming this app for giving me false hope, not going to lie.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Calendar Invite Confusion - Wrong Timezone Chaos
    # User received a meeting invite that seems off and is trying to figure out timezones
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "calendar_timezone_chaos",
        [
            ("My coworker sent me a calendar invite and I genuinely cannot tell what timezone it's in.", False),
            ("Does this say 2pm EST or PST? Because those are very different things.", True),
            ("Like, if it's EST, that's 11am my time and I have a conflict.", False),
            ("I asked her and she said 'afternoon.' Thanks, that clears up nothing lmao.", False),
            ("Look at the invite details though. It literally doesn't specify a timezone anywhere.", True),
            ("I swear to God, corporate calendar tools are designed to cause maximum confusion.", False),
            ("I'm just going to show up at both times and see what happens, I guess.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Phone Settings Deep Dive - Hidden Features Hunt
    # User is exploring phone settings and finding stuff they never knew existed
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "settings_deep_dive",
        [
            (
                "I went into my phone settings for one thing and now I've been in here for 40 minutes discovering stuff.",
                False,
            ),
            ("Did you know there's a setting that measures how level your phone is? Like a spirit level?", False),
            ("Wait, what does this accessibility option do? Look at this.", True),
            ("BRO, why does everything look like this now? It changed all my colors. What did I press?", True),
            ("Ok, fixed it. But look at this other thing I found. Back tap to screenshot. That's actually sick.", True),
            ("I'm going down a rabbit hole right now, but honestly, these hidden features are amazing.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Voice Memo Accidental Recording - Cringe Discovery
    # User finds a voice memo that was recorded accidentally and it's embarrassing
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "voice_memo_accident",
        [
            ("So apparently my phone recorded a voice memo in my pocket for like 45 minutes last Tuesday.", False),
            ("I just found it in my recordings and it's mostly just rustling noises.", False),
            ("But at the 12 minute mark you can hear me singing in the grocery store. I'm mortified.", False),
            ("The timestamp on this recording says it started at 6pm, right when I left work. See?", True),
            ("I wonder if anyone heard me singing. I was doing full harmonies, apparently.", False),
            ("Look at how long this file is though. 45 minutes of pocket audio lmao.", True),
            ("Deleting this immediately. Nobody can ever hear this.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Widget Customization Obsession - Perfect Home Screen
    # User is spending way too long making their home screen look aesthetic
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "widget_customization",
        [
            ("I have spent three hours customizing my home screen and I am not done yet.", False),
            ("This widget layout is clean though, right? Like the color coordination.", True),
            ("I changed the weather widget font four times already because nothing felt right.", False),
            ("Ok, but look at this setup now with the small calendar next to the battery widget.", True),
            ("Wait, the clock widget is like 2 pixels off center and I can see it. This is killing me.", True),
            ("On God, I need to stop, but I physically cannot leave it like this until it's perfect.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Software Update Debate - To Update or Not to Update
    # User is agonizing over whether to install a software update
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "software_update_debate",
        [
            ("My phone has been begging me to update for like 3 weeks and I keep hitting remind me later.", False),
            ("Last time I updated, it killed my battery life and made everything slower.", False),
            ("But this update page says it fixes security stuff, so maybe I should.", True),
            ("What even are these new features though? Look at this list. Half of them seem useless.", True),
            ("Someone on Reddit said it bricked their phone, so that's fun.", False),
            ("You know what, I'm just going to do it tonight and pray. Updating right now, wish me luck.", False),
            ("If my phone doesn't turn back on tomorrow, it's been real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Do Not Disturb Scheduling - Peace and Quiet Quest
    # User is setting up DND schedules to stop notifications from ruining their life
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "dnd_scheduling",
        [
            (
                "I get like 200 notifications a day and I'm losing my mind, so I'm finally setting up do not disturb.",
                False,
            ),
            ("Wait, does this schedule mean it turns on at 10pm or off at 10pm? I can't tell.", True),
            ("I want it on from 10pm to 8am and also during my work focus time from 9 to 12.", False),
            ("Ok, but look at this. There's like 15 different focus modes now. When did they add all these?", True),
            ("This one says gaming focus. Like, look at the icon. Who even uses that?", True),
            ("Alright, I set it up. If I miss anything important between 10 and 8, that's a tomorrow problem.", False),
            ("Actually, wait. Do alarms still go off during DND? Because if not, I'm screwed.", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

"""Photos and camera scenarios: selfie filters, gallery cleanup, portrait mode, panoramas, photo dumps."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Selfie Filter Comparison - Trying Different Filters
    # Friends comparing selfie filters and debating which ones look best
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "selfie_filter_comparison",
        [
            ("Ok, I'm trying to find a good filter for this selfie right now, hold on.", False),
            ("The first one makes my skin look weirdly smooth like I'm an AI or something.", False),
            ("Wait, ok, try looking at this one though. It's way more natural.", True),
            ("Not going to lie, I think the original no-filter version looks better than both, to be honest.", False),
            ("Does this angle look weird to you or am I being paranoid?", True),
            ("Whatever, I'm just going to post it raw. No filter gang lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Gallery Storage Cleanup - Too Many Photos
    # User overwhelmed by phone storage and trying to delete old photos
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "gallery_storage_cleanup",
        [
            ("Bro, my phone just told me I have 14000 photos and my storage is full. I'm screaming.", False),
            ("Like, why did I save 30 pics of my lunch from 2023? That's insane.", False),
            ("Wait, this one is actually a good photo though. Should I keep it?", True),
            ("Ok, never mind, I just found a whole folder of blurry screenshots from God knows when.", False),
            ("Look at how many duplicates I have of the same sunset. This is embarrassing.", True),
            ("I swear to God, I'm never letting my gallery get this bad again.", False),
            ("This photo is from like 3 years ago but it goes so hard, look.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Portrait Mode Background Blur Fail
    # Portrait mode mangling the edges and making things look weird
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "portrait_mode_blur_fail",
        [
            ("Portrait mode really said let me just eat half your ear off today.", False),
            ("Look at this, it literally blurred out part of my face. What is this?", True),
            ("The background is crispy but my hair is just gone on the left side, see that?", True),
            ("I took like 15 portrait shots yesterday and every single one had something wrong.", False),
            ("This one right here is the worst. Look at my arm, it looks like it's melting.", True),
            ("Honestly, regular mode with manual editing after is just better at this point.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Panorama Attempt Gone Wrong - Warped Image
    # Trying to capture a panorama and getting hilariously distorted results
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "panorama_gone_wrong",
        [
            ("Tried to take a panorama at the beach today and I literally cannot stop laughing.", False),
            ("Look at what it did to this random dude walking by. He has three legs now.", True),
            ("And the horizon line is just vibing at like a 30 degree angle, see that?", True),
            ("I moved the phone too fast and now half the boardwalk just vanished from existence lmao.", False),
            ("There's this part where the sky glitches into the sand and it's lowkey art, not going to lie.", False),
            ("Going to try again tomorrow but I'm not holding my breath, for real.", False),
            ("Wait, check this other one. It's even worse, somehow the dog is stretched out like taffy.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Photo Dump Selection - Picking The Best Pics To Post
    # Curating the perfect photo dump for instagram from a bunch of options
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "photo_dump_selection",
        [
            ("Ok, I need your help picking photos for my dump post. This is serious business.", False),
            ("Which one of these should be the first slide? Tell me right now.", True),
            ("This pic came out so good, like the lighting was insane.", True),
            ("I don't know if I should include the food pic or if that's too basic. What do you think?", False),
            ("Ok, but look at this candid one my friend took. I didn't even know she was shooting.", True),
            ("Going to go with 7 slides. I think that's the sweet spot.", False),
            ("See this last one? Perfect closer or nah?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Burst Mode Accident - 200 Nearly Identical Photos
    # Accidentally holding down the shutter and getting a million duplicate pics
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "burst_mode_accident",
        [
            ("So I accidentally held down the camera button and took 247 photos in like 3 seconds.", False),
            ("My phone literally lagged after that. It was processing for a solid minute.", False),
            ("They're all basically identical except in this one my eyes are closed lmaooo.", True),
            ("I have to delete like 245 of these but I don't know which ones to keep.", False),
            ("Ok, this one is the sharpest right here. You can actually see the detail.", True),
            ("Honestly, burst mode should come with a warning label or something, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Night Mode Comparison - Dark Photos Test
    # Testing out night mode vs regular mode in low light conditions
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "night_mode_comparison",
        [
            ("Went out last night and wanted to test how good night mode actually is.", False),
            ("Check this one without night mode. It's literally just a black screen with some lights.", True),
            ("Now look at the same spot with night mode on. It's like a completely different scene.", True),
            ("The colors always come out kind of weird though, like everything gets this yellow tint.", False),
            ("I took some at the concert too, but you have to hold so still for 3 seconds. It's annoying.", False),
            ("To be honest, my old phone couldn't even dream of shooting in the dark like this.", False),
            ("This one came out the cleanest. Look how sharp the buildings are at midnight.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Food Photography Attempts - Getting The Perfect Shot
    # Trying to photograph food before eating it and struggling with the setup
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "food_photography_attempts",
        [
            ("My pasta is getting cold because I've been trying to get the perfect overhead shot for 5 mins.", False),
            ("Does this angle work or should I go more from the side?", True),
            ("The lighting in this restaurant is so trash. Everything looks orange.", False),
            ("Ok, I moved the plate near the window and this one is way better, look.", True),
            ("Bruh, my friend already finished eating while I was still adjusting the napkin placement.", False),
            ("This is the one right here. The steam is visible and everything, it's perfect.", True),
            ("Ok, I'm eating now. The photo can wait for editing later lol.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Group Photo Coordination Disaster
    # Trying to get everyone to look good in the same photo and failing repeatedly
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "group_photo_disaster",
        [
            ("We took like 40 group photos at dinner and not a single one has everyone looking good.", False),
            ("Look at this one. Sarah's eyes are closed and Jake is literally mid-sneeze.", True),
            ("This one is almost perfect but someone's thumb is covering the corner, see?", True),
            ("I told everyone to smile at the same time but apparently that was too much to ask.", False),
            ("We asked this random stranger to take one for us and they got the worst angle possible.", False),
            ("On God, this is the best we got and Marcus is still blinking, look.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Photo Editing App Comparison - Which Filter App Is Best
    # Comparing different photo editing apps and their filter results
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "photo_editing_app_comparison",
        [
            ("Ok, so I edited the same photo in three different apps to see which one is better.", False),
            ("This is the Lightroom version. The colors are super clean but maybe too perfect.", True),
            ("Now see this one from VSCO. It's got that film grain aesthetic going on.", True),
            ("Snapseed did something weird to the shadows though. Look at the bottom half.", True),
            ("I think for everyday posts VSCO wins, but for like professional stuff, Lightroom easy.", False),
            ("Lowkey might just stick with the iPhone built-in editor. It's gotten so much better.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Screenshots Folder Chaos - Full Of Random Captures
    # Discovering the horror of an unorganized screenshots folder
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "screenshots_folder_chaos",
        [
            ("I just opened my screenshots folder and it's 3000 images of pure chaos.", False),
            ("There's receipts from 2022 mixed with memes mixed with random convos I screenshotted.", False),
            ("Why did I screenshot this? It literally makes no sense, look at it.", True),
            ("Oh wait, I remember that one lmaooo. It was from that Twitter drama last summer.", False),
            ("I'm going to need like 2 hours to sort through all this, honestly.", False),
            ("This right here is a screenshot of a screenshot of a screenshot. How does that even happen?", True),
            ("Deleting everything from before 2025. I'm not even going to look, I don't care anymore.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Live Photo Funny Moments
    # Discovering hilarious moments captured in live photos before the actual shot
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "live_photo_funny_moments",
        [
            ("I just realized live photos capture the second before you take the pic and it's gold.", False),
            ("Press and hold on this one. Watch what happens right before the smile.", True),
            ("She was literally mid-fall in one of them and the actual photo still looks perfect.", False),
            ("I've been going through old live photos and some of these are unhinged.", False),
            ("The audio on this one is killing me. Someone yelled at the exact wrong moment.", True),
            ("Going to start a whole album of just the live photo fails, to be honest.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Camera Quality Comparison - New Phone Vs Old
    # Comparing photos taken on a new phone versus the old one side by side
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "camera_quality_comparison",
        [
            ("Just upgraded from my iPhone 12 to the 16 Pro and the camera difference is wild.", False),
            ("Look at this photo I took on the old phone vs the same angle on the new one.", True),
            ("The zoom on this thing is actually insane. See how far I can go without it getting blurry.", True),
            ("My old phone could never do macro shots like that. The detail is actually insane.", False),
            ("Honestly, the front camera upgrade alone was worth it. Selfies are so much sharper now.", False),
            ("I took the same pic of my cat on both phones and the 16 makes her look majestic.", False),
            ("Check this comparison right here. The dynamic range isn't even close.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Photo Memories/Flashback Notification Reactions
    # Reacting to throwback photos that the phone surfaces from years ago
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "photo_memories_flashback",
        [
            ("My phone just hit me with a 4 years ago today memory and I'm not ok.", False),
            ("We looked so young. What the heck, that was literally just college.", False),
            ("Look at what it pulled up though. This was the best night ever.", True),
            ("I completely forgot about this trip until my phone reminded me just now.", False),
            ("That whole era was so different. Right now I miss everyone from those days so much.", False),
            ("Apple really said let me randomly make you cry on a Tuesday morning lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Trying To Take A Good ID/Passport Photo
    # Struggling to take an acceptable photo for an ID or passport application
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "passport_photo_struggle",
        [
            ("I need a passport photo and I have literally never looked good in one of these.", False),
            ("Does this look ok or do I look like a serial killer? Be honest.", True),
            ("They said no smiling but my resting face is so aggressive looking, bruh.", False),
            ("Ok, I adjusted the lighting and tried again. See, this version is a bit better, right?", True),
            ("My friend said I should go to CVS but I refuse to pay 15 dollars for a photo I hate.", False),
            ("I'm just going with the last one I took. I don't care anymore, I just need the passport.", False),
            ("Going to look at this cursed photo every time I travel for the next 10 years. Fantastic.", False),
        ],
    ),
]

__all__ = ["DATA"]

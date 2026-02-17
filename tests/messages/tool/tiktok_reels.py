"""TikTok and Reels scenarios: FYP discoveries, viral videos, duets, trending sounds, mukbang, BookTok."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: FYP Algorithm Accuracy - User freaked out by how targeted their feed is
    # Someone scrolling their For You Page and realizing TikTok knows them too well
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "fyp_algorithm_eerily_accurate",
        [
            (
                "Bro, my FYP is literally reading my mind right now. I was JUST talking about buying an air fryer and now every other video is air fryer content.",
                False,
            ),
            ("Like look at this one, it literally says best air fryer under 50 dollars.", True),
            ("I never even searched for it on TikTok, that's the scary part.", False),
            ("And then this video right here is about meal prepping, which I was also googling last night.", True),
            ("Not going to lie, the algorithm is lowkey terrifying but also kind of useful. I can't even lie.", False),
            ("Wait, see this ad too. They are literally selling me the exact model I looked at on Amazon.", True),
            ("I'm convinced my phone is listening to me, for real for real, no cap.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Viral Dance Challenge - Watching and roasting dance attempts
    # Friends watching various people attempt a trending dance challenge
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "viral_dance_challenge",
        [
            ("Have you seen that new dance challenge? Everyone is doing it. It looks so easy but it's not.", False),
            ("Okay, check this girl out. She absolutely killed it, like the footwork is insane.", True),
            ("I saw one dude try it and he completely ate it up, not going to lie.", False),
            ("I tried learning it yesterday and almost broke my ankle, not even joking.", False),
            ("This one right here is the original that started it all.", True),
            ("The sound already has like 4 million videos, which is wild.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Mukbang Reactions - Watching someone demolish an absurd amount of food
    # User sending reactions while watching a mukbang video in real time
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "mukbang_reactions",
        [
            (
                "Yo, I just opened TikTok and the first thing on my FYP is some dude eating a raw onion like an apple. What is wrong with people?",
                False,
            ),
            ("I can't stop watching mukbangs lately. It's becoming a problem, to be honest.", False),
            (
                "Look at the size of this plate, bruh. That's like 8 pounds of noodles. No human should eat that in one sitting.",
                True,
            ),
            ("The sounds are so gross but I literally cannot scroll away. I don't know what's wrong with me.", False),
            (
                "This part right here where he just inhales the entire lobster tail in one bite. I'm going to be sick.",
                True,
            ),
            (
                "Why do these videos get like 12 million views? Who is watching this stuff besides me, apparently?",
                False,
            ),
            (
                "I swear to God, TikTok is rotting my brain, but here I am at 3am watching someone eat 50 chicken wings.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: BookTok Recommendations - Discovering books through TikTok
    # Someone falling down the BookTok rabbit hole and building a reading list
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "booktok_recommendations",
        [
            (
                "BookTok has completely taken over my FYP and honestly I'm not mad about it. I haven't read this much since high school.",
                False,
            ),
            (
                "See, this girl is literally sobbing over the ending of Fourth Wing and now I need to read it immediately.",
                True,
            ),
            ("I already ordered three books this week because of TikTok. My wallet is crying.", False),
            ("This review right here convinced me to start the ACOTAR series everyone keeps talking about.", True),
            (
                "Not going to lie, some of these recommendations are lowkey mid though. Not everything BookTok hypes up is actually good.",
                False,
            ),
            ("But look at this stack she has. The taste is immaculate. I need her entire list.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Duet Chain Madness - Reacting to an increasingly chaotic duet chain
    # User discovering a long chain of duets and losing it at each layer
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "duet_chain_madness",
        [
            (
                "I just found the longest duet chain I've ever seen on TikTok and each one gets progressively more unhinged.",
                False,
            ),
            ("Okay, so this is the original video. It's just some guy singing off key, right? Pretty normal.", True),
            ("Then check this duet where someone harmonized with him but made it actually good somehow.", True),
            ("But then THIS person duetted that and added a whole beat and now it's a banger?", True),
            ("By the fifth duet the screen is so tiny you can barely see the original lmao.", False),
            ("I love when TikTok does this, to be honest. The collaborative energy is unmatched.", False),
            ("Someone needs to compile all these into one video because the chain is getting hard to follow.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Trending Sound Obsession - Hearing the same audio on every video
    # User going crazy hearing the same trending sound on repeat across their feed
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "trending_sound_obsession",
        [
            ("If I hear that oh no oh no oh no no no sound one more time, I'm deleting this app, I swear.", False),
            ("It's on literally every single video on my FYP right now. I counted seven in a row.", False),
            ("Like, this video didn't even need that sound. It's a cooking tutorial, why?", True),
            ("And this one too, it's just a dog sitting there. They slapped the sound on for no reason.", True),
            (
                "I miss when TikTok sounds were actually creative and not just the same three audios recycled forever.",
                False,
            ),
            ("Wait, okay, this use of it is actually kind of funny, not going to lie. Look at the timing.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: TikTok Live Gone Wrong - Watching a chaotic live stream unfold
    # Someone narrating a messy TikTok live to a friend in real time
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tiktok_live_gone_wrong",
        [
            ("BRUH, get on TikTok right now. This live is absolutely falling apart.", False),
            ("This girl started a chill makeup stream and then her roommate walked in screaming about dishes.", True),
            ("The chat is going insane right now. Everyone is sending skull emojis lmao.", False),
            ("Look at her face. She has no idea what to do. She just froze with the mascara wand in her hand.", True),
            ("Now the roommate is reading the comments and getting even more mad. It's pure chaos.", False),
            ("She just ended it. Oh my God, that was the most unhinged live I've ever witnessed.", False),
            ("I should've screen recorded it, to be honest. That's never happening again.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Cooking TikTok Fail - Recipe looked easy on TikTok but was a disaster
    # User tried a viral TikTok recipe and it went horribly wrong
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "cooking_tiktok_fail",
        [
            ("So remember that pasta recipe I saw on TikTok that looked super easy? Yeah, it did not go well.", False),
            (
                "The video made it look like a five minute thing but I was in the kitchen for two hours and it still looked wrong.",
                False,
            ),
            ("See, this is what it was supposed to look like in the video. All creamy and perfect.", True),
            ("And THIS is what mine looks like lmao. It's giving prison food realness.", True),
            (
                "I followed the recipe exactly. I don't know what went wrong. Maybe my stove is broken or something.",
                False,
            ),
            ("Honestly, I'm just going to order DoorDash. These TikTok recipes be lying to us, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Pet TikTok Spiral - Falling into an endless loop of cute animal videos
    # Someone who cannot stop watching pet content on their FYP
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "pet_tiktok_spiral",
        [
            ("I have been on pet TikTok for three hours straight. I am not okay. Someone take my phone.", False),
            ("Look at this golden retriever wearing little boots in the snow. I am going to cry.", True),
            (
                "Earlier I saw a cat that kept slapping its owner every time they tried to work. Dead serious, the funniest thing I've seen all week.",
                False,
            ),
            ("I don't even have a pet but this app is making me want to adopt like four animals immediately.", False),
            ("This one right here with the raccoon that thinks it's a dog has me on the floor.", True),
            ("My screen time report is going to be embarrassing tomorrow, but honestly worth it.", False),
            ("Okay, one more video then I'm going to sleep. I keep saying that, but peep this puppy.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: TikTok Drama and Beef - Creators going at each other publicly
    # User updating a friend on creator beef unfolding across multiple videos
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tiktok_creator_beef",
        [
            (
                "Okay, so there is MASSIVE beef happening on TikTok right now between these two creators and it's getting ugly.",
                False,
            ),
            ("Basically one of them called the other out in a video yesterday and it blew up overnight.", False),
            ("Check this response video. The passive aggression is through the roof.", True),
            (
                "Then this comment right here from the other one saying receipts are coming had everyone lose their minds.",
                True,
            ),
            ("The stitch where she exposes the DMs though. Look at what he actually said vs what he claimed.", True),
            (
                "Not going to lie, I don't even follow either of them, but TikTok drama is my guilty pleasure. I can't look away.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Satisfying Videos Compilation - Oddly satisfying content binge
    # User mesmerized by satisfying content and sharing favorites
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "satisfying_videos_binge",
        [
            ("I've been stuck on satisfying TikTok for an hour and my brain is just mush at this point.", False),
            ("This soap cutting one is so good. Watch how clean the slices are.", True),
            (
                "And this pressure washing video, oh my God. Look at the difference between the left side and the right side.",
                True,
            ),
            (
                "I don't know why my brain craves this content so much, but I physically cannot scroll past these videos.",
                False,
            ),
            ("See this kinetic sand one. The way it just crumbles is doing something to my serotonin.", True),
            ("I used to think people who watched these were weird, but here I am at 2am fully hypnotized.", False),
            ("This one with the paint mixing though. The colors blending right here is genuinely beautiful.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: TikTok Shop Scam Vibes - Suspicious promoted products
    # User skeptical about TikTok Shop products being aggressively pushed
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tiktok_shop_scam_vibes",
        [
            (
                "TikTok Shop is getting out of hand. Every other video is someone trying to sell me something now.",
                False,
            ),
            (
                "Like look at this product. There's no way this actually works. It's literally a flashlight that claims to remove wrinkles.",
                True,
            ),
            (
                "And the reviews are all clearly fake. Have you noticed that every TikTok Shop review sounds exactly the same?",
                False,
            ),
            (
                "This creator used to make normal content but now every video is just an ad for random stuff. It's sad, honestly.",
                False,
            ),
            (
                "Check this one out though. 90 percent off a designer bag? Yeah, okay, sure buddy. That's definitely real.",
                True,
            ),
            (
                "They always put ad in tiny letters at the top but design the whole video to look organic, which feels scammy.",
                False,
            ),
            (
                "I'm convinced half these products are just AliExpress stuff with a 300 percent markup, not going to lie.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Reels vs TikTok Debate - Comparing content across platforms
    # Friends arguing about whether Instagram Reels or TikTok has better content
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reels_vs_tiktok_debate",
        [
            (
                "Okay, but Reels is literally just recycled TikTok content like three weeks later. I will die on this hill.",
                False,
            ),
            ("See this reel right here? I saw the exact same video on TikTok last month with way more views.", True),
            (
                "The algorithm on Reels is trash too. It keeps showing me stuff from 2024. Like, hello, update please.",
                False,
            ),
            (
                "TikTok just hits different though. The editing, the sounds, the duets. Reels doesn't have that energy.",
                False,
            ),
            (
                "Look at this side by side. Same creator posted on both and the TikTok version has 10x the engagement.",
                True,
            ),
            (
                "To be honest, I use both, but only because Reels is right there when I open Instagram. It's not like I go looking for it.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Dark Humor TikTok Rabbit Hole - Edgy comedy content binge
    # Someone deep in the dark humor side of TikTok late at night
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "dark_humor_rabbit_hole",
        [
            (
                "Dark humor TikTok at 4am hits completely different. I am laughing at things that should not be funny.",
                False,
            ),
            ("This one is so wrong but I cannot stop replaying it. The delivery is too perfect.", True),
            ("I know I shouldn't be laughing, but bruh, the timing on that punchline caught me so off guard.", False),
            ("Look at this comment section. Everyone is saying see you in hell lmao.", True),
            ("That dude's whole page is just unhinged content. How does he not get banned, honestly?", False),
            ("Okay, I need to go to sleep. I'm losing brain cells, but also this last one is wild. Look.", True),
            ("My sense of humor is completely broken at this point. Thanks, TikTok.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: GRWM Routine Content - Get Ready With Me video reactions
    # User watching and reacting to GRWM content and morning routines
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "grwm_routine_content",
        [
            (
                "I am so addicted to GRWM videos even though my own routine is literally just splash water on face and leave.",
                False,
            ),
            (
                "This girl has a 47 step skincare routine and her skin looks exactly the same as mine. Make it make sense.",
                True,
            ),
            (
                "The aesthetic is immaculate though, not going to lie. Like everything is color coordinated and the lighting is perfect.",
                False,
            ),
            (
                "See this part where she does her eyeliner in one stroke? I could never. That takes me twenty minutes minimum.",
                True,
            ),
            (
                "These routines are so unrealistic. Nobody actually wakes up at 5am to journal and do yoga and make a smoothie bowl every single day.",
                False,
            ),
            (
                "But look at this one. She's actually real about it. Messy room, coffee stain on her shirt. That's more like it.",
                True,
            ),
            (
                "Honestly, I watch these instead of actually getting ready, which is counterproductive but whatever.",
                False,
            ),
        ],
    ),
]

__all__ = ["DATA"]

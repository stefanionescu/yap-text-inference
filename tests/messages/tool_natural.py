"""Natural multi-turn and ambiguous reaction prompts."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ── NATURAL MULTI-TURN CONVERSATIONS ─────────────────────────────────────────────
    (
        "cooking_recipe_troubleshooting",
        [
            ("I'm trying to make this pasta carbonara recipe I found online", False),
            (
                "The instructions say to mix the eggs with the pasta while it's hot, but I'm worried about scrambling them",
                False,
            ),
            ("Can you check the recipe? I have it open on my screen", True),
            ("The comments section says some people had issues with the eggs curdling", False),
            ("I'm wondering if I should let the pasta cool down a bit first", False),
            ("What do you think about this approach?", True),
        ],
    ),
    (
        "dating_app_profile_feedback",
        [
            ("I'm updating my dating profile and I'm not sure if my bio is too long or too short", False),
            ("I wrote something about my hobbies and what I'm looking for, but I feel like it might be boring", False),
            ("Can you read it and tell me what you think?", True),
            ("I'm trying to sound interesting without trying too hard, you know?", False),
            ("Also, I'm debating between these two photos for my main picture", False),
            ("Which one do you think shows me better?", True),
            ("The first one is from a hiking trip and the second is from a friend's wedding", False),
        ],
    ),
    (
        "work_email_draft_review",
        [
            ("I need to send an email to my boss about taking time off next month", False),
            ("I've drafted it but I'm not sure if the tone is right", False),
            ("I want to be professional but also friendly, and I'm worried it might come across as too casual", False),
            ("Can you look at what I wrote?", True),
            (
                "I'm asking for a week off to visit family, which I think is reasonable since I haven't taken much time off this year",
                False,
            ),
            ("Does this sound okay?", True),
        ],
    ),
    (
        "apartment_hunting_decision",
        [
            ("I'm apartment hunting and I found two places that are both in my budget", False),
            ("The first one is closer to work but smaller, and the second one is bigger but further away", False),
            ("I've been going back and forth on which one to choose", False),
            ("I took screenshots of both listings with all the details", False),
            ("Can you help me compare them?", False),
            ("Here's the first one", True),
            ("Here's the second one", True),
            (
                "I'm leaning toward the first one because the commute would be so much better, but the second one has a balcony which I really want",
                False,
            ),
            ("What's your take?", False),
        ],
    ),
    (
        "code_error_debugging_session",
        [
            ("I've been working on this Python script for hours and I keep getting the same error", False),
            (
                "It's a type error where it says I'm trying to concatenate a string with an integer, but I'm pretty sure I converted everything to strings",
                False,
            ),
            ("I've added print statements everywhere to debug it but I'm still stuck", False),
            ("Can you look at the error message and the code around line 45?", True),
            ("I think the issue might be in how I'm parsing the JSON response from the API", False),
            ("The data structure is nested and I'm wondering if I'm accessing it wrong", False),
            ("See this part here?", True),
        ],
    ),
    (
        "outfit_choice_for_event",
        [
            ("I have a job interview tomorrow and I can't decide what to wear", False),
            (
                "It's for a tech startup so I know it's probably more casual than a traditional corporate job, but I still want to look professional",
                False,
            ),
            ("I've laid out three different outfits on my bed", False),
            ("Can you help me pick which one looks best?", False),
            ("Here they are", True),
            (
                "The first one is a navy blazer with dark jeans, the second is a button-down with chinos, and the third is a sweater with dress pants",
                False,
            ),
            ("I'm worried the first one might be too casual even for a startup", False),
            ("What do you think?", False),
        ],
    ),
    (
        "social_media_post_draft",
        [
            ("I'm trying to write a post for LinkedIn about a project I just finished at work", False),
            (
                "I want to share what I learned but I don't want to sound like I'm bragging or being too self-promotional",
                False,
            ),
            ("I've written a few drafts and I'm not sure which version works best", False),
            ("Can you read through this one and tell me if the tone is right?", True),
            (
                "I'm trying to focus on the technical challenges I overcame rather than just saying 'look what I did'",
                False,
            ),
            ("Does this come across that way?", True),
        ],
    ),
    (
        "furniture_assembly_confusion",
        [
            ("I'm trying to assemble this IKEA bookshelf and the instructions are confusing me", False),
            (
                "Step 4 says to attach part A to part B using connector C, but I can't figure out which way part A should face",
                False,
            ),
            ("The diagram isn't very clear and I'm worried I'm going to put it together wrong", False),
            ("Can you look at the instruction manual?", True),
            (
                "I've already taken everything out of the box and I don't want to have to take it apart if I do it wrong",
                False,
            ),
            ("Does this orientation look right?", True),
        ],
    ),
    (
        "restaurant_menu_decision",
        [
            ("I'm at this new restaurant and the menu is huge, I can't decide what to order", False),
            ("Everything sounds good but I'm trying to decide between the pasta dish and the steak", False),
            ("The descriptions are pretty vague though, like 'house special pasta' doesn't tell me much", False),
            ("I'm looking at reviews on my phone to see what people recommend", False),
            ("Can you check this review? They posted a photo of the pasta", True),
            ("It looks really good but I'm also curious about the steak", False),
            ("Do you see any reviews with steak photos?", True),
        ],
    ),
    (
        "gym_form_check",
        [
            ("I've been working on my deadlift form and I want to make sure I'm doing it right", False),
            ("I've watched a bunch of YouTube videos but I'm still not confident about my setup", False),
            ("I recorded a quick video of myself doing a few reps", False),
            ("Can you watch it and tell me if my form looks okay?", True),
            ("I'm particularly worried about my back rounding, which I know is dangerous", False),
            ("Does it look like I'm keeping my back straight enough?", True),
            ("I'm lifting 135 pounds which is about 60% of my max, so I should be able to maintain good form", False),
        ],
    ),
    (
        "travel_planning_itinerary",
        [
            ("I'm planning a trip to Japan next month and I've put together a rough itinerary", False),
            ("I have 7 days and I want to see Tokyo, Kyoto, and maybe Osaka if there's time", False),
            ("I've mapped out the days but I'm worried I'm trying to pack too much in", False),
            ("Can you look at my schedule?", True),
            (
                "I'm planning to do Tokyo for 3 days, then take the bullet train to Kyoto for 2 days, and maybe do a day trip to Osaka",
                False,
            ),
            ("But I'm wondering if I should cut Osaka and spend more time in Kyoto instead", False),
            ("What do you think about this plan?", False),
        ],
    ),
    (
        "art_project_feedback_request",
        [
            ("I've been working on this digital art piece for a client and I'm not sure if it's finished", False),
            ("I've been tweaking it for hours and I think I might be overthinking it", False),
            ("The client gave me some feedback but I'm not sure if I've addressed all their concerns", False),
            ("Can you look at the current version?", True),
            ("They wanted it to feel more energetic and vibrant, so I've added more color and movement", False),
            ("But now I'm worried it might be too busy", False),
            ("Does this look balanced to you?", True),
        ],
    ),
    (
        "phone_setup_troubleshooting",
        [
            ("I just got a new phone and I'm trying to set up my email accounts", False),
            (
                "The setup wizard is asking me to configure something called IMAP settings, which I've never heard of",
                False,
            ),
            ("I have all my passwords and server information, but I'm not sure where to enter it", False),
            ("Can you look at this screen? I'm not sure what to put in each field", True),
            (
                "My email provider sent me instructions but they're not matching up with what I'm seeing on the phone",
                False,
            ),
            ("Does this configuration look right?", True),
        ],
    ),
    (
        "presentation_slide_feedback",
        [
            ("I'm working on a presentation for work and I'm stuck on this one slide", False),
            (
                "It's supposed to explain our quarterly results but I feel like it's too cluttered with information",
                False,
            ),
            ("I've tried simplifying it but now I'm worried it doesn't have enough detail", False),
            ("Can you look at this slide and tell me what you think?", True),
            ("I'm trying to balance being informative with keeping it readable for the audience", False),
            (
                "The presentation is for executives who don't have a lot of time, so I want to make sure the key points are clear",
                False,
            ),
            ("Does this version work better?", True),
        ],
    ),
    (
        "plant_care_identification",
        [
            ("I got this plant as a gift and I have no idea what it is or how to take care of it", True),
            ("I've been watering it every few days but the leaves are starting to turn yellow", False),
            ("I'm worried I'm either overwatering or underwatering it", False),
            ("Can you look at this photo? Maybe you can help me identify what kind of plant it is", True),
            (
                "The person who gave it to me didn't tell me what it was, and I want to make sure I'm taking care of it properly",
                False,
            ),
            ("Do you think the yellowing is from too much water or not enough?", False),
        ],
    ),
    # ── AMBIGUOUS REACTIONS: Same phrases, different contexts ─────────────────────
    # These test phrases like "wtf", "bro that's wild", "omg no way" in visual vs non-visual contexts
    (
        "wild_reaction_to_visible_video",
        [
            (
                "I've been scrolling through TikTok for the past hour and the algorithm is feeding me the craziest stuff tonight",
                False,
            ),
            ("There's this one creator who does these insane parkour videos in abandoned buildings", False),
            (
                "Most of them are clearly edited but some look genuinely dangerous, like I can't tell if it's real",
                False,
            ),
            ("Okay wait this one is actually insane, he's jumping between buildings with no safety gear at all", True),
            ("bro that's wild, how is he not dead yet", True),
            ("Like there's no way this is legal, someone's gonna get hurt doing this stuff", False),
            ("Oh my god he just did a backflip off a crane", True),
        ],
    ),
    (
        "wild_reaction_to_story_nonvisual",
        [
            ("So I was at the grocery store earlier and the weirdest thing happened to me", False),
            (
                "I was in the cereal aisle minding my own business when this random guy comes up and starts talking to me",
                False,
            ),
            ("He was convinced I was his cousin's friend from college or something, super insistent about it", False),
            ("I kept telling him he had the wrong person but he would not let it go, it was so awkward", False),
            ("bro that's wild, what did you do", False),
            ("I eventually just grabbed my stuff and walked away but he followed me for like two more aisles", False),
            (
                "So uncomfortable, I ended up leaving without half the things on my list just to get away from him",
                False,
            ),
        ],
    ),
    (
        "wtf_reaction_to_screenshot_content",
        [
            ("I've been arguing with this guy in my DMs for like three hours now and I'm losing my mind", False),
            ("It started because I made a comment on his post about coffee and he took it way too personally", False),
            ("Now he's writing these huge paragraphs trying to prove that I don't know anything about espresso", False),
            ("Like sir, I worked as a barista for four years, I think I know what I'm talking about", False),
            ("wtf is that thing he just sent me", True),
            ("Is that supposed to be a threat or is he just being dramatic? I genuinely can't tell anymore", True),
            (
                "This conversation has gone completely off the rails and I kind of want to screenshot it for Twitter",
                False,
            ),
        ],
    ),
    (
        "wtf_reaction_to_news_nonvisual",
        [
            ("Did you hear about what happened at that tech conference yesterday? It's all over my feed", False),
            ("Apparently the CEO of that AI startup got up on stage and just started crying mid-presentation", False),
            ("Like full on sobbing, couldn't get through his slides, had to be escorted off stage by his team", False),
            ("wtf is that about, did something happen to him or was it just pressure", False),
            ("People are saying it might have been a mental breakdown from all the investor pressure lately", False),
            ("The stock dropped like 15% immediately after, investors are freaking out", False),
            ("I feel bad for the guy honestly, that kind of public breakdown must be humiliating", False),
        ],
    ),
    (
        "omg_no_way_visual_gaming_moment",
        [
            ("I've been grinding this raid boss for literally six hours straight and I'm about to lose it", False),
            ("My team keeps wiping at the same phase because people won't follow the mechanics properly", False),
            ("We've tried everything - different compositions, different strategies, nothing is working", False),
            ("Okay we're going in again, this is attempt number forty-something at this point", False),
            ("omg no way, I think we're actually gonna do it this time", True),
            ("HE'S AT ONE PERCENT HEALTH EVERYONE JUST STAY ALIVE PLEASE", False),
            ("WE DID IT, SIX HOURS BUT WE FINALLY KILLED THIS STUPID BOSS", False),
            ("I'm literally shaking right now, that was the most stressful gaming experience of my life", False),
        ],
    ),
    (
        "omg_no_way_reacting_to_ai_info",
        [
            ("Wait so you're telling me that octopuses have three hearts and blue blood?", False),
            ("omg no way, that's actually insane, I had no idea", False),
            ("What else do you know about them? They're like aliens that evolved on Earth basically", False),
            ("They can also change color AND texture? Like their whole skin can mimic their surroundings?", False),
            ("That's so cool, I need to watch a documentary about this now", False),
            ("Do they actually have good memories too? I heard they can remember people", False),
            ("This is making me feel bad about eating calamari honestly, they're too smart for that", False),
        ],
    ),
    (
        "thats_crazy_visual_dating_app",
        [
            ("I've been on this dating app for two weeks and the people on here are absolutely unhinged", False),
            ("Like I thought Tinder was bad but this app takes it to a whole new level of weird", False),
            ("The bios alone could fill an entire comedy special, people have no self-awareness", False),
            ("Okay you have to see this one profile I just came across", True),
            ("that's crazy, who writes that in their bio and thinks it's a good look", True),
            ("And look at his photos, every single one is a mirror selfie in the gym with the flash on", True),
            (
                "I matched with someone normal earlier but at this point I'm just here for the entertainment value",
                False,
            ),
            ("The bar is so low and people are still finding ways to trip over it", False),
        ],
    ),
    (
        "thats_crazy_reacting_to_friend_story",
        [
            ("My roommate just told me the most insane story about her date last night", False),
            ("So she met this guy for dinner and everything was going fine for the first twenty minutes", False),
            ("Then he excuses himself to go to the bathroom and just... never comes back", False),
            ("Like she waited for an hour thinking maybe he had an emergency or something", False),
            ("Turns out he literally left through the back door and she got stuck with the bill", False),
            ("that's crazy, who does that to someone? Did she try to contact him after?", False),
            ("She texted him and he blocked her immediately, no explanation, nothing", False),
            ("I would be so mad, that's genuinely one of the rudest things I've ever heard", False),
        ],
    ),
    (
        "look_at_this_mess_visual_home",
        [
            ("I've been trying to organize my apartment all day and I think I made it worse somehow", False),
            ("I started with the closet and now everything is just spread across every surface in my room", False),
            ("There's stuff on my bed, my desk, the floor, I literally have nowhere to sit right now", False),
            ("I found things I forgot I even owned, like stuff from three apartments ago", False),
            ("look at this mess, I genuinely don't know how to recover from this point", True),
            ("I think I need to just throw half of it away but I have such a hard time getting rid of things", False),
            ("Maybe I should just shove it all back in the closet and pretend this never happened", False),
            ("No okay I'm committed now, I'm going to finish this even if it takes all night", False),
        ],
    ),
    (
        "look_at_this_figuratively_work",
        [
            ("My boss just sent out the new project requirements and I'm already exhausted reading them", False),
            ("We have two weeks to deliver something that should realistically take at least two months", False),
            ("And of course he wants daily progress reports on top of actually doing the work", False),
            ("look at this mess of a timeline he put together, it's completely unrealistic", False),
            ("There's no way the team can hit these milestones without working weekends the whole time", False),
            ("I've already pushed back twice but he just keeps saying we need to be more efficient", False),
            ("At some point I'm going to have to escalate this because the burnout is going to be real", False),
            ("Either we get more time or more people, there's no other way this gets done properly", False),
        ],
    ),
    (
        "no_freaking_way_visual_coincidence",
        [
            ("So I've been watching this true crime documentary and something really weird just happened", False),
            ("They started talking about this cold case from the 90s and showing photos of the victim", False),
            ("And I swear the victim looks exactly like my coworker's profile picture on LinkedIn", False),
            ("Like not similar, I mean identical features, same hair, same everything", False),
            ("no freaking way, look at this side by side comparison I just made", True),
            ("Am I going crazy or is this actually uncanny? It's freaking me out a little", True),
            ("It's probably just a coincidence but my brain is doing that thing where it won't let it go", False),
            ("I'm definitely not going to mention this to my coworker, that would be so weird", False),
        ],
    ),
    (
        "no_freaking_way_lottery_nonvisual",
        [
            ("My uncle just called and told me the most ridiculous thing that happened to him today", False),
            ("He bought a lottery ticket at the gas station like he does every week, just a random pick", False),
            ("Apparently he won, not the jackpot but still a pretty significant amount", False),
            ("no freaking way, how much did he actually win?", False),
            ("He said it's enough to pay off his car and still have some left over for a vacation", False),
            (
                "That's insane, he's been playing the same numbers for twenty years and never won more than fifty bucks",
                False,
            ),
            ("I need to start buying lottery tickets apparently, maybe luck runs in the family", False),
            ("He's being really chill about it but I know he's probably freaking out inside", False),
        ],
    ),
    (
        "dude_what_visual_glitch",
        [
            ("I've been playing this game for hours and it's been totally fine until like two minutes ago", False),
            ("Now something is seriously wrong, the graphics are completely broken", False),
            ("All the textures are missing and the characters are just floating T-poses everywhere", False),
            ("I tried restarting but it's still doing this weird thing, I've never seen anything like it", False),
            ("dude what is happening to my screen right now", True),
            ("Is this a known bug or did my graphics card just decide to die on me", True),
            ("I really hope it's just the game because I cannot afford to replace hardware right now", False),
            ("Let me try reinstalling, maybe something got corrupted in the last update", False),
        ],
    ),
    (
        "dude_what_disbelief_conversation",
        [
            ("I just had the most bizarre conversation with my landlord and I'm still processing it", False),
            ("He knocked on my door to tell me he's selling the building and I have sixty days to move out", False),
            ("dude what, sixty days? That's barely enough time to find a new place in this market", False),
            ("I've been living here for five years, paid rent on time every single month", False),
            ("And the best part is he wants me to show the apartment to potential buyers", False),
            ("Like you're kicking me out and you want me to help you sell? Absolutely not", False),
            ("I need to look into my rights here because this feels like it can't be legal", False),
            ("Definitely going to talk to a lawyer before I sign anything or agree to move out", False),
        ],
    ),
    (
        "yo_check_this_visual_meme",
        [
            ("I've been in a group chat with my college friends and they've been sending memes all day", False),
            ("Most of them are pretty mid but occasionally someone drops something actually good", False),
            ("We have this ongoing competition for who can find the most obscure funny content", False),
            ("I think I finally found one that's going to win, it's so stupid but so perfect", False),
            ("yo check this out, this is exactly our humor", True),
            ("The comments section is even funnier, people are losing their minds over this", True),
            ("I'm going to drop this in the group chat and wait for the reactions", False),
            ("If this doesn't get at least ten laughing emojis I'm going to be disappointed", False),
        ],
    ),
    (
        "yo_check_this_verbal_story",
        [
            ("My brother called me yesterday and told me about this situation at his job", False),
            ("yo check this out, so apparently his company has been secretly recording all their meetings", False),
            ("Not just for notes or whatever, but like actually monitoring what people say", False),
            ("Someone found out because they got a performance review that quoted things verbatim", False),
            ("Things they said in what they thought were casual conversations with coworkers", False),
            ("The whole office is freaking out and talking about unionizing or something", False),
            ("I told him to start looking for a new job because that's such a massive red flag", False),
            ("Companies that do stuff like that usually have way worse things going on behind the scenes", False),
        ],
    ),
    (
        "hold_up_visual_price_check",
        [
            ("I've been online shopping for a new laptop and comparing prices across different sites", False),
            ("The same exact model has wildly different prices depending on where you look", False),
            ("I found one site that's like three hundred dollars cheaper than everywhere else", False),
            ("But it seems almost too good to be true, like is this a scam or what", False),
            ("hold up look at this price, there's no way this is legit right?", True),
            ("The website looks professional enough but the reviews are all kind of generic", True),
            ("I'm tempted but I also don't want to get scammed out of my money", False),
            ("Maybe I'll just pay the extra money and buy from a store I actually trust", False),
        ],
    ),
    (
        "hold_up_verbal_clarification",
        [
            ("So my friend is telling me about this new diet she's trying and it sounds insane", False),
            ("Apparently you only eat during a four hour window and fast the rest of the day", False),
            ("hold up, so you're telling me you don't eat anything for twenty hours straight?", False),
            ("How do you have energy to do anything? I would pass out by noon", False),
            ("She says you get used to it and it's supposed to be really good for metabolism", False),
            ("I don't know, that sounds extreme even by diet standards", False),
            ("I'll stick with my normal eating schedule, I like food too much for that", False),
            ("But hey if it works for her, more power to her I guess", False),
        ],
    ),
    (
        "are_you_seeing_this_visual_live",
        [
            ("I'm watching this live stream right now and something really weird is happening", False),
            ("The streamer was just playing normally and then they got up and walked off camera", False),
            ("That was like ten minutes ago and they still haven't come back", False),
            ("The chat is going crazy trying to figure out what's going on", False),
            ("are you seeing this, someone just walked into frame and it's definitely not the streamer", True),
            ("This is getting kind of creepy honestly, who is that person in their house", True),
            ("Oh wait they're talking now, apparently it's just their roommate pranking them", False),
            ("My heart was actually racing for a minute there, I thought we were witnessing something bad", False),
        ],
    ),
    (
        "are_you_seeing_this_figurative",
        [
            ("Have you been following the drama in that celebrity divorce case?", False),
            ("are you seeing this mess, they're airing all their dirty laundry in public", False),
            ("Every day there's a new allegation or leaked text message or something", False),
            ("I know I shouldn't care about celebrity gossip but this is too entertaining", False),
            ("The lawyers must be making so much money off all these filings and counter-filings", False),
            ("At some point they need to just split their stuff and move on with their lives", False),
            ("But I guess when you have that much money, the fighting is part of the process", False),
            ("I'll probably keep following it until they finalize everything, can't help myself", False),
        ],
    ),
    (
        "this_cant_be_real_visual_product",
        [
            ("I was browsing Amazon for random stuff and found the most ridiculous product listing", False),
            ("Someone is actually selling this and people have bought it based on the reviews", False),
            ("The description is written completely seriously like it's a legitimate product", False),
            ("But the photos are clearly photoshopped and the whole thing looks like a joke", False),
            ("this can't be real, look at what they're charging for this thing", True),
            ("And the reviews are all five stars but they read like they were written by AI", True),
            ("I'm honestly tempted to buy it just to see what actually shows up", False),
            ("This is why I have trust issues with online shopping sometimes", False),
        ],
    ),
    (
        "this_cant_be_real_disbelief_verbal",
        [
            ("My sister just told me she's dropping out of law school to become an influencer", False),
            ("She's two years into a three year program and she wants to quit now", False),
            ("this can't be real, she worked so hard to get into that school", False),
            ("Our parents are going to absolutely lose their minds when they find out", False),
            ("I get that being a lawyer isn't for everyone but she was doing so well", False),
            ("She says she already has sponsors lined up but I'm skeptical", False),
            ("I tried to talk her out of it but she seems pretty set on this decision", False),
            ("I guess I just have to support her even if I think it's a mistake", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

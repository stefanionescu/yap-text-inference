"""Streaming and entertainment scenarios: Netflix picks, YouTube rabbit holes, Spotify playlists, podcasts."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Netflix Decision Paralysis - Can't Pick What to Watch
    # User scrolling through Netflix unable to commit to anything
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "netflix_decision_paralysis",
        [
            ("I've been scrolling for like 40 minutes and I still haven't picked anything to watch lmao.", False),
            ("Wait, okay, this one looks kind of interesting, not going to lie.", True),
            ("Have you seen this before? The description sounds insane.", True),
            ("Actually, never mind, the reviews are mid. I just checked.", False),
            ("Okay, what about this one right here? It's got like a 95% match for me.", True),
            ("You know what, forget it. I'm just going to rewatch The Office again.", False),
            ("I do this literally every single night. I don't know why I even bother looking.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: YouTube Algorithm Rabbit Hole - 3am Deep Dive
    # User stuck in a YouTube rabbit hole way too late at night
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "youtube_3am_rabbit_hole",
        [
            ("Bro, it is 3am and I started watching one video about black holes and now I'm here.", False),
            ("Look at what YouTube is recommending me right now.", True),
            ("See this video title right here? 'Medieval cooking with no electricity.' How did I get here?", True),
            ("This thumbnail right here is so unhinged. I have to click it.", True),
            ("Okay, wait, this video is actually fire though. The editing is crazy.", False),
            ("I have work in 4 hours but honestly this is worth it.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Spotify Wrapped Reactions - Sharing Stats
    # User sharing and reacting to their Spotify Wrapped results
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "spotify_wrapped_reactions",
        [
            ("MY WRAPPED JUST DROPPED and I am not okay.", False),
            ("Look at my top artist. This is so embarrassing.", True),
            ("364 hours on one artist. That cannot be right. There's no way.", False),
            ("Check this out though. My top song, I played it 847 times.", True),
            ("See this genre it says I listen to? I don't even know what that is.", True),
            ("Everyone's posting theirs on stories and not going to lie, mine is the most unhinged.", False),
            ("I'm lowkey proud of it though, like yes, I am that person.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Podcast Recommendation Exchange - Sharing Favorites
    # Friends exchanging podcast recs and discussing episodes
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "podcast_recommendation_swap",
        [
            ("Okay, you NEED to start listening to podcasts for real. They've changed my life.", False),
            ("I listened to this one episode on my commute yesterday and it blew my mind.", False),
            ("Here, look at this one right here. It's only like 45 min.", True),
            ("The host is so funny. You'll get hooked immediately, I promise.", False),
            ("Also, this other one is about psychology and it's lowkey addicting.", True),
            ("I go through like 3 episodes a day at this point, not going to lie.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: YouTube Shorts Addiction - Can't Stop Scrolling
    # User trapped in the infinite scroll of YouTube Shorts
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "youtube_shorts_addiction",
        [
            ("I accidentally opened Shorts 2 hours ago and I literally cannot stop.", False),
            ("Look at my screen time for today. It's actually embarrassing.", True),
            ("Lmao, wait. Look at this one. This is the funniest thing I've ever seen.", True),
            ("I tried to close the app three times and I keep going back.", False),
            ("See this cat video right here? I've replayed it like 20 times.", True),
            ("Okay, I'm putting my phone down for real this time. Goodnight.", False),
            ("...Okay, one more, then I'm done. I swear.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Binge-Watching Debate - Show Recommendations
    # Friends debating what to binge next and sharing opinions
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "binge_watching_debate",
        [
            ("I finished that show you recommended last week and it was mid, to be honest.", False),
            ("The ending was so bad I actually got mad about it.", False),
            ("Okay, but have you seen this new one everyone's talking about?", True),
            ("Look at the cast list right here. It's stacked.", True),
            ("I'm going to start it tonight. I already cleared my whole schedule lol.", False),
            ("Last time I said that I watched 10 episodes in one sitting, so wish me luck.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Spotify Playlist Curation - Making the Perfect Playlist
    # User obsessively curating a playlist and sharing progress
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "spotify_playlist_curation",
        [
            ("I've been working on this playlist for like 3 hours and it's still not right.", False),
            ("Look at this gap in the energy between track 3 and 4. It kills the whole vibe.", True),
            ("Look at the tracklist so far. Does this order make sense?", True),
            ("I keep going back and forth on whether this song fits the mood.", False),
            ("See this transition right here from track 7 to 8? That's perfect.", True),
            ("Okay, I think it's done. 47 songs and 2 hours 38 minutes of pure vibes.", False),
            ("Wait, no. I need to add one more. Hold on.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Documentary Deep Dive - Found Something Fascinating
    # User discovered a wild documentary and can't stop talking about it
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "documentary_deep_dive",
        [
            ("Dude, I just watched the most insane documentary I've ever seen in my life.", False),
            ("It's about this cult in the 70s and the stuff they did is WILD.", False),
            ("Look at this part right here where they show the compound.", True),
            ("See this photo right here of all the cars lined up? It's actually unreal.", True),
            ("Check this scene out. The interview with the ex-member is haunting.", True),
            ("I went down a whole Wikipedia rabbit hole after and it gets even crazier.", False),
            ("I swear to God, documentaries like this are better than any scripted show.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Netflix Price Complaints + Password Sharing Drama
    # User ranting about Netflix pricing and the password crackdown
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "netflix_price_password_drama",
        [
            ("Netflix raised their prices AGAIN, bro. I literally cannot with this company.", False),
            ("I've been sharing my mom's account for years and now they're cracking down.", False),
            ("Look at this email they sent me about unauthorized access.", True),
            ("They want me to pay 8 bucks extra a month for an extra member slot. Are you serious?", False),
            ("See this plan comparison right here? The basic one doesn't even have HD anymore.", True),
            ("I'm honestly about to just cancel and go back to pirating lmao.", False),
            ("Wait, actually, look at this bundle deal. Is this new?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: YouTube Video Essay Obsession - Long Form Content
    # User obsessed with 3+ hour video essays on random topics
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "youtube_video_essay_obsession",
        [
            ("I just watched a 4 hour video essay about the fall of a Minecraft server and it was peak cinema.", False),
            ("These long form YouTube videos are genuinely better than most movies, not going to lie.", False),
            ("This creator right here makes the best ones. Look at their channel.", True),
            ("They posted a new one that's 5 hours long and I'm so excited to watch it tonight.", False),
            (
                "See this runtime right here? Five hours and twenty three minutes. On a kids' game. I love the internet.",
                True,
            ),
            (
                "I need to stop watching these at 1am though, because I always say one more hour and then it's 6am.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Music Discovery - Spotify Discover Weekly Finds
    # User excited about songs Spotify's algorithm found for them
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "spotify_discover_weekly_finds",
        [
            ("Discover Weekly actually ate this week. Every single song is a banger.", False),
            ("Look at this artist they put on there. I've never heard of them before.", True),
            ("Check this album cover out. It's so aesthetic. I can't stop staring at it.", True),
            ("The algorithm really said 'I know you better than you know yourself,' huh?", False),
            ("See this recommendation right here? How did it know I'd love this?", True),
            ("I already added like 8 songs to my main playlist, to be honest.", False),
            ("Going to listen to the rest on my walk later. This is actually so good.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: True Crime Podcast Spiral - Can't Stop Listening
    # User deep in a true crime podcast binge and getting paranoid
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "true_crime_podcast_spiral",
        [
            ("Okay, so I started listening to true crime podcasts and now I trust nobody.", False),
            ("I binged like 12 episodes today while cleaning and I'm lowkey terrified.", False),
            ("Look at this episode description. Does this not sound absolutely insane?", True),
            ("Look at this timeline right here of how they caught the guy. It's wild.", True),
            ("I double locked my door tonight because of this episode, not going to lie.", False),
            ("See this review right here? Someone said they couldn't sleep for a week after listening.", True),
            ("Honestly same, but I'm still going to keep listening because I'm unwell.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Anime Streaming Wars - Crunchyroll vs Others
    # User frustrated about anime being split across platforms
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "anime_streaming_wars",
        [
            ("Why is every anime on a different streaming service now? This is actually so annoying.", False),
            ("I need Crunchyroll for one show, Netflix for another, and now HIDIVE for a third.", False),
            ("Look at this lineup for next season. Half of it is Crunchyroll exclusive.", True),
            ("This show right here is the one I'm most hyped for and of course it's on the one I don't have.", True),
            ("I watched the first season on Netflix and now season 2 moved to a whole different app.", False),
            ("At this point I'm paying more for anime than I pay for actual food, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Spotify Daylist Reactions - AI-Generated Playlist Names
    # User losing it over the absurd names Spotify gives their daylists
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "spotify_daylist_reactions",
        [
            ("The Spotify Daylist names are getting out of control and I'm here for it.", False),
            ("Look at what it called my Monday morning playlist.", True),
            ("It said 'wistful bedroom indie Tuesday afternoon.' Like, what does that even mean?", False),
            ("Check this one out from yesterday. It literally called me out.", True),
            ("See the vibe description right here? 'Melancholic overthinking evening.' HELLO.", True),
            ("Honestly, it's more accurate than any personality test I've ever taken.", False),
            ("I screenshot every single one now because they're too good to lose.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: YouTube Premium Debate + Ad Complaints
    # User fed up with YouTube ads debating whether to get Premium
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "youtube_premium_ad_debate",
        [
            ("I just got THREE unskippable ads in a row on YouTube. I'm actually losing my mind.", False),
            ("Look at this ad right here. It's literally 45 seconds long and I can't skip it.", True),
            ("Everyone keeps telling me to just get Premium but it's like 14 bucks a month.", False),
            ("I've been using an adblocker but they keep finding ways to block the blocker.", False),
            ("See this popup right here? YouTube detected my adblocker again, bruh.", True),
            ("At this point they're literally holding my videos hostage until I pay up.", False),
            ("Fine, I'll get the free trial but I'm canceling before they charge me, I swear to God.", False),
        ],
    ),
]

__all__ = ["DATA"]

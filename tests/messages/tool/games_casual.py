"""Games and casual gaming scenarios: Wordle, gacha, Candy Crush, Pokemon GO, chess, mobile ads."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Wordle Daily Struggle - Sharing Grid Without Spoilers
    # Friend texts about their Wordle attempt and shares the colored grid
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "wordle_daily_struggle",
        [
            ("Bro, today's Wordle absolutely destroyed me, not going to lie.", False),
            ("I used all 6 tries and barely got it on the last row.", False),
            ("Look at this grid though, the colors are so misleading.", True),
            ("I had three greens by row two and still almost lost. How is that even possible?", False),
            ("See that yellow tile right there? It threw me off so hard.", True),
            ("Wordle is getting way harder lately, or maybe I'm just getting dumber lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Gacha Pull Excitement - Rare Character Obtained
    # Player just hit a rare pull and is losing their mind showing the result
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "gacha_pull_excitement",
        [
            ("YOOO I JUST HIT THE CRAZIEST PULL OF MY LIFE!", False),
            ("Check this out, I'm literally shaking right now.", True),
            ("That's the limited 5 star on the first ten pull, are you kidding me?", True),
            ("I was saving for months and didn't even need pity this time.", False),
            ("Look at the animation, it did the special one with the shooting stars.", True),
            ("Everyone in the Discord is so mad at me right now lmaooo.", False),
            ("Is this character even good though? Like, check these stats.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Candy Crush Impossible Level - Stuck for Days
    # Player has been stuck on a level and showing how unfair the board is
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "candy_crush_stuck",
        [
            ("I have been on this level for literally a week. I can't do it.", False),
            ("Look at this board. Tell me how I'm supposed to clear that in 15 moves.", True),
            ("The chocolate keeps spreading faster than I can break it.", False),
            ("See all those blockers on the right side? There's no way to reach them.", True),
            ("I refuse to buy boosters on principle, but I swear to God this game wants my money.", False),
            ("Watch, I'm going to try one more time and get the exact same garbage layout.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Pokemon GO Community Day - Hunting Shinies
    # Friends coordinating during community day and showing catches
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "pokemon_go_community_day",
        [
            ("Oh my God, community day just started and there's already a shiny on my screen!", True),
            ("I clicked on it so fast, bro, please don't run.", False),
            ("I CAUGHT IT! LOOK AT THIS BEAUTIFUL THING!", True),
            (
                "The IVs are trash though, not going to lie, but I don't care. It's shiny, that's all that matters.",
                False,
            ),
            ("Where are you guys at? I'm by the Pokestop near the fountain.", False),
            ("There's a cluster spawn right here, you need to come over.", True),
            ("I've caught like 200 already and only two shinies. Rates feel nerfed, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Chess Blunder Replay - Analyzing a Bad Move
    # Player reviewing a game where they made a terrible blunder
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "chess_blunder_replay",
        [
            ("Dude, I just threw the most won game of my life. I'm actually sick.", False),
            ("Look at this position. I was completely winning, material up and everything.", True),
            ("And then I played this move right here. See where my knight went?", True),
            ("I hung my queen for literally no reason. It wasn't even a complicated position.", False),
            ("The engine says I went from plus 7 to minus 12 in one move lmao.", False),
            ("Check this eval bar. It just drops straight down like a cliff.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Mobile Game Ad Interruption - Pure Rage
    # Player raging about unskippable ads in a free mobile game
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "mobile_ad_rage",
        [
            ("I literally cannot play this game for more than 30 seconds without an ad.", False),
            ("Look at this. It's a full 30 second unskippable video ad for some scam app.", True),
            ("And the X button is microscopic and in a different spot every time.", False),
            ("Look, it literally redirected me to the app store from that tiny fake X button.", True),
            ("See this? Another ad already and I haven't even finished the level.", True),
            ("I'm deleting this garbage. No game is worth sitting through this many ads, to be honest.", False),
            ("Wait, they just offered me ad-free for $9.99 a WEEK. Are they insane?", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: In-App Purchase Temptation - Wallet in Danger
    # Player debating whether to spend real money on a limited time offer
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "iap_temptation_regret",
        [
            ("Okay, so there's this limited bundle in the shop and it's only here for 6 hours.", False),
            ("Look at what's in it though. Tell me that's not worth it.", True),
            ("It's $25 but you get like 5000 gems plus an exclusive skin.", False),
            ("I already spent way too much this month on games, but this deal is actually good.", False),
            ("Check this price compared to just buying gems normally.", True),
            ("Ugh, I bought it. I have zero self control, for real.", False),
            ("Don't judge me, okay? I know what I am.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Among Us Lobby Drama - Trust Issues and Accusations
    # Group chat blowing up during an Among Us session
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "among_us_lobby_drama",
        [
            ("BRO, WHO JUST VENTED? I SAW SOMEONE VENT!", False),
            ("Look at where the body is. It was right next to electrical.", True),
            ("I was in medbay doing the scan. You can literally check the logs.", False),
            ("This is so suspicious. Why are you accusing me when you were nowhere near admin?", False),
            ("See the map right here? There's no way you made it from cafeteria that fast.", True),
            ("I'm voting you out. I don't care if we lose, I know it's you.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Subway Surfers High Score - Chasing Personal Best
    # Player going for a new record and narrating the run
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "subway_surfers_highscore",
        [
            ("Okay, I'm going for a new high score right now. Wish me luck.", False),
            ("I'm already past my old record and still going, oh my God.", False),
            ("Look at this score right now. I'm at 2.4 million.", True),
            ("My hands are literally sweating. I can't mess up.", False),
            ("NOOO, I JUST CRASHED INTO A TRAIN! I had so much momentum going.", False),
            ("Check this final score though. It's still a new personal best.", True),
            ("Lowkey might grind for 3 mil tonight. I'm so close.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Mobile Game Recommendations - What to Play
    # Friends exchanging mobile game recs and showing screenshots
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "mobile_game_recs",
        [
            ("I'm so bored. I need a new mobile game to play. Any suggestions?", False),
            ("I've been playing this one tower defense game and it's actually fire.", False),
            ("Look at the graphics. For a mobile game, this is pretty solid, right?", True),
            ("It's free too, but like actually free, not pay to win garbage.", False),
            ("Check this app store rating. 4.8 stars with a million reviews.", True),
            ("Okay, downloading it right now. If it's trash, I'm blaming you.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Clash Royale Deck Frustration - Losing Streak
    # Player tilting hard and blaming their deck/matchups
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "clash_royale_tilt",
        [
            ("I've lost 8 games in a row and dropped 300 trophies. I'm about to uninstall.", False),
            ("Look at this matchup. How am I supposed to beat maxed out cards with my levels?", True),
            ("See my deck? Everyone says it's meta, but I keep getting hard countered.", True),
            ("Look at this replay. He spammed the laughing emote after beating me with ebarbs rage.", True),
            ("I swear the matchmaking is rigged. They always give me the worst possible counter.", False),
            ("Maybe I should just copy whatever deck this guy is using.", False),
            ("Look at his card levels compared to mine though. This is so unfair.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: 2048 Almost Winning - So Close Yet So Far
    # Player nearly hits the 2048 tile and chokes at the end
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "2048_almost_won",
        [
            ("I have never been this close to getting the 2048 tile before, oh my God.", False),
            ("Look at this board. I'm literally one merge away.", True),
            ("But see this stupid 2 tile right here? It's blocking everything.", True),
            ("If I swipe left I lose, but if I swipe right I might get stuck too.", False),
            ("What move should I make here? I'm scared to touch anything.", True),
            ("I swiped up and it spawned a 4 in the worst possible spot. I'm done.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Gacha Pity System - Whale Gone Wrong
    # Player hit pity and still got the wrong character, total despair
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "gacha_pity_despair",
        [
            ("I just spent $200 trying to get the banner character and I lost the 50/50.", False),
            ("Look at what I got instead. It's the one character I already have at max.", True),
            ("See my pull history. This is actually criminal.", True),
            ("90 pulls to hit pity and then the game gives me a dupe. I'm so done.", False),
            ("I need to hide my bank statement from myself lmao. This is genuinely bad.", False),
            ("I'm never spending on gacha again. I say this every time, but I mean it now, for real.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Pokemon GO Raid Coordination - Legendary Boss Fight
    # Group trying to organize enough people for a legendary raid
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "pokemon_go_raid_coord",
        [
            ("There's a Mewtwo raid at the gym on 5th street and it starts in 10 min.", False),
            ("We need at least 5 people. Who can make it?", False),
            ("I'm already here. Look at the lobby, it's just me and one random so far.", True),
            ("Hurry up, the timer is ticking down. I don't want to waste my remote pass.", False),
            ("Okay, we got 6 people in, let's gooo! Look at this lineup, we might actually win.", True),
            ("WE BEAT IT and I got 14 premiere balls to catch it!", False),
            ("Look at this. It keeps breaking out of excellent throws. Are you serious right now?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Mobile Game Battery Drain - Phone on Fire
    # Player complaining about how much battery their games eat
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "mobile_game_battery_drain",
        [
            ("Why does Genshin eat my battery like it's a competitive sport?", False),
            ("I started playing 40 minutes ago at 80% and look at my battery now.", True),
            ("It's at 23% and my phone is literally hot enough to cook on.", False),
            ("Check this battery usage screen. Genshin used 47% in one session.", True),
            ("I have a portable charger but even that can't keep up with how fast it drains.", False),
            ("Lowkey might just play on PC from now on. My phone can't handle it anymore.", False),
        ],
    ),
]

__all__ = ["DATA"]

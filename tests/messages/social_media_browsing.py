"""Social media browsing scenarios: Instagram stories, Twitter/X threads, Reddit posts, Facebook Marketplace."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Explore Page Rabbit Hole - Instagram Algorithm Trap
    # User falls down an Instagram explore page spiral late at night
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "ig_explore_rabbit_hole",
        [
            ("I've been on the explore page for like an hour, not going to lie, my algorithm is unhinged.", False),
            ("Look at this video though, it's a cat riding a Roomba in a shark costume.", True),
            ("Instagram keeps feeding me these and I can't stop scrolling.", False),
            ("Wait, this one is even better, oh my God.", True),
            ("I should probably go to sleep but the explore page has me in a chokehold right now.", False),
            ("Okay, one more scroll and I'm done for real this time.", False),
            ("Bruh, see this reel right here, who even makes these?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Ratio Moment - Someone Got Destroyed in Replies
    # User witnessing a brutal ratio on Twitter/X in real time
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "twitter_ratio_destruction",
        [
            ("Someone just got absolutely destroyed on Twitter, you need to see this.", False),
            ("Look at this ratio, it's at 50k quote tweets and only 2k likes.", True),
            ("This reply right here is what ended him, honestly.", True),
            ("The guy tried to double down too, which made it so much worse.", False),
            (
                "Not going to lie, I almost feel bad, but then I reread his original take and nah, he deserved it.",
                False,
            ),
            ("This screenshot of his deleted tweet is circulating now too.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: AITA Judgment - Reddit Moral Debate
    # User reading an Am I The Asshole post and reacting to the drama
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reddit_aita_debate",
        [
            ("Okay, so I'm reading this AITA post and I'm losing my mind.", False),
            ("This person wants to know if they're the AH for uninviting their sister from the wedding.", False),
            ("Check this part where she explains why though.", True),
            ("I don't know how anyone is voting NTA on this, she's clearly unhinged.", False),
            ("See this comment right here, it breaks down exactly why she's wrong.", True),
            ("The update is even wilder, apparently the sister showed up anyway.", False),
            ("Look at the edit at the bottom, I swear to God this family needs therapy.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Sketchy Listings - Facebook Marketplace Finds
    # User browsing Facebook Marketplace and finding suspicious deals
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "fb_marketplace_sketchy",
        [
            ("Facebook Marketplace is a fever dream, I swear to God.", False),
            ("Look at this listing, someone's selling a couch for 20 bucks.", True),
            ("Those stains are suspicious, I honestly wouldn't touch that thing.", True),
            ("Also, why is every listing in my area either a scam or haunted furniture?", False),
            ("This one says slightly used, but look at the condition, bruh.", True),
            ("I saw one yesterday that was literally just a photo of an empty room.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Story Stalking - Checking an Ex's Instagram
    # User checking their ex's Instagram stories and spiraling
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "ig_story_stalking_ex",
        [
            ("Okay, don't judge me, but I'm on my ex's Instagram stories right now.", False),
            ("They posted like eight stories tonight, which is not normal for them.", False),
            ("See this one, they're clearly at our spot, like the restaurant we used to go to.", True),
            ("And who is that person in the background of this story?", True),
            ("Never mind, I zoomed in and it's just their cousin. I'm being insane.", False),
            ("I need to stop doing this, to be honest, it's not healthy.", False),
            ("But look at this caption though, is that about me or am I delusional?", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Viral Thread - Hot Take Discourse on Twitter/X
    # User following a viral thread with increasingly unhinged takes
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "twitter_viral_hot_take",
        [
            ("Twitter is absolutely unhinged today, there's this thread going viral.", False),
            ("The original take was already bad, but look at how people are responding.", True),
            ("Someone quote tweeted it with the most unhinged reply I've ever seen.", False),
            ("Every time I think the discourse can't get worse, it does.", False),
            ("This take right here might be the worst one yet, just read it.", True),
            ("It already has 40k likes too, which is genuinely concerning.", False),
            ("See the community note they slapped on it lmao.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Relationship Advice - Reddit Thread Reading
    # User deep in a Reddit relationship advice thread
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reddit_relationship_advice",
        [
            ("I've been reading relationship advice threads for two hours now and I feel like a therapist.", False),
            ("This one is wild, the person found their partner's secret Reddit account.", False),
            ("Look at the post history they found though, that's actually crazy.", True),
            ("All the comments are telling them to leave, and honestly, yeah.", False),
            ("The top comment is so well written it made me emotional, not going to lie.", False),
            ("Check this response from someone who went through the same thing.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Haggling Horror - Facebook Marketplace Negotiation Disaster
    # User sharing a terrible haggling experience on Marketplace
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "fb_marketplace_haggling",
        [
            ("I listed my old desk on Marketplace for 80 bucks and the lowballers are killing me.", False),
            ("This person offered me 15 dollars and a gift card to Applebee's, I can't make this up.", True),
            ("Then when I said no, they hit me with this guilt trip message, look.", True),
            ("Someone else asked if I'd deliver it 45 minutes away for free, like, be serious right now.", False),
            ("Oh, and see this conversation, this person asked if it was still available then ghosted.", True),
            ("Marketplace people are a different breed, on God, I'm just going to donate the thing.", False),
            (
                "Wait, look at this new message. Someone's offering full price, but their profile is brand new and has no photo.",
                True,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Influencer vs Reality - Instagram Comparison
    # User comparing influencer photos to reality on Instagram
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "ig_influencer_vs_reality",
        [
            ("I just found this account that posts influencer photos next to the unedited versions.", False),
            ("Look at this one, the waist editing is so obvious, the doorframe is literally warped.", True),
            ("This influencer got caught because a fan took a photo at the same event.", False),
            ("See the comparison side by side, it's not even close.", True),
            ("Honestly, it makes me feel better about myself knowing how fake everything is.", False),
            ("This one right here is the worst though, she photoshopped abs onto her dog.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Elon Drama - Twitter/X Reactions to Latest Chaos
    # User reacting to the latest Elon Musk Twitter/X controversy
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "twitter_elon_drama",
        [
            ("Bro, what did Elon do now? Twitter is on fire again.", False),
            ("Apparently he changed something and everyone's freaking out, I can't keep up.", False),
            ("Look at the trending tab, it's all about this.", True),
            ("This meme about it is killing me though, not going to lie.", True),
            ("People are threatening to leave again, like they do every month.", False),
            ("See this tweet from a developer explaining what actually changed.", True),
            ("We'll all still be here tomorrow, let's be honest lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Conspiracy Deep Dive - Reddit Rabbit Hole
    # User going down a Reddit conspiracy theory rabbit hole at 3am
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reddit_conspiracy_deep_dive",
        [
            ("It's 3am and I'm on a conspiracy subreddit. I don't even know how I got here.", False),
            ("This post has like 47 awards and it connects celebrities to some random company.", False),
            ("Look at this chart they made connecting everything, it's insane.", True),
            ("I know it's probably all nonsense, but the way they laid it out is kind of convincing.", False),
            ("See this photo they zoomed in on, there's supposedly a hidden symbol.", True),
            ("Okay, yeah, never mind, they just said the earth is flat. I'm out, goodnight.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Close Friends Story Drama - Instagram Inner Circle
    # User discovering they were removed from someone's close friends list
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "ig_close_friends_drama",
        [
            ("Wait, so apparently Jess has a close friends story and I'm not on it anymore.", False),
            ("Maya just showed me and I'm lowkey offended, to be honest.", False),
            ("Look at what she posted on there, it's clearly about our friend group.", True),
            ("She used to have me on close friends like two weeks ago, I don't know what changed.", False),
            ("This screenshot Maya sent me of the story is so passive aggressive, read it.", True),
            ("I'm not going to confront her about it, but like, it's weird, right?", False),
            ("See, she posted a regular story too and it's all normal, like nothing happened.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Quote Tweet Battles - Twitter/X Discourse War
    # User watching a quote tweet war unfold between two accounts
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "twitter_quote_tweet_war",
        [
            (
                "There's a full on quote tweet war happening right now between two huge accounts and it's beautiful.",
                False,
            ),
            ("Look at how this started, it was over the most pointless thing ever.", True),
            ("Then this guy quote tweeted with receipts from 2019 and it escalated real fast.", False),
            ("This clapback right here is genuinely one of the best I've ever seen.", True),
            ("Both of them are getting ratio'd now, which is hilarious.", False),
            ("Check the quote tweets on this one, the reactions are gold.", True),
            ("They both just went private lmao, I can't breathe.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Front Page Find - Random Reddit Discovery
    # User finds something interesting on Reddit's front page and shares it
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "reddit_front_page_find",
        [
            ("Yo, I just found the most random thing on Reddit's front page.", False),
            ("Look at this post, some guy built a functioning computer inside Minecraft.", True),
            ("The comments are full of people losing their minds, and honestly, same.", False),
            ("See this reply where someone explains how it actually works though.", True),
            ("Apparently it took him like 8 months, which is both impressive and concerning.", False),
            ("This top comment just says touch grass and it has 20k upvotes lmao.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Screen Time Guilt - Social Media Cleanse Contemplation
    # User feeling guilty about screen time and considering a detox
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "social_media_cleanse_guilt",
        [
            ("My screen time report just hit me like a truck. I spent 7 hours on social media yesterday.", False),
            ("I keep saying I'll do a cleanse, but then I open Instagram out of muscle memory.", False),
            ("I read an article last week about dopamine and scrolling and it genuinely scared me.", False),
            ("Everyone I know is chronically online though, so it feels normal.", False),
            ("Look at my screen time breakdown, this is actually embarrassing.", True),
            ("TikTok is 3 hours and Reddit is 2 hours, like, when did I even do that?", False),
            ("See this app that's supposed to help you limit usage, has anyone tried it?", True),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

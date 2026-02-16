"""Messaging and notification scenarios: text receipts, DMs, email overload, group chats, Discord, Slack."""
# ruff: noqa: E501  # Test data - long strings are intentional

from .tool_types import ToolDefaultEntry

TOOL_MESSAGES: list[ToolDefaultEntry] = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Read Receipts Betrayal - Left on Read Drama
    # User spiraling over being left on read, checking timestamps on screen
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "read_receipts_betrayal",
        [
            ("I sent that text like three hours ago and nothing back. I'm losing it, not going to lie.", False),
            ("Look at this though, they literally read it at 2:47 and just said nothing.", True),
            ("See how it says read underneath? That means they opened it and chose violence.", True),
            ("I shouldn't have double texted honestly, that was my bad.", False),
            ("But for real, who leaves someone on read for this long? That's actually insane behavior.", False),
            ("This timestamp right here is what kills me, read at 2:47 and it's almost 6 now.", True),
            ("I'm not going to text again. I'm just going to pretend I don't care lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: DM Slide Attempt - Someone Messaged Them Unexpectedly
    # User shocked by an unexpected DM showing it to a friend
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "dm_slide_attempt",
        [
            ("Bruh, you will NOT believe who just slid into my DMs.", False),
            ("Look at this message they sent me, I literally screamed.", True),
            ("We haven't talked since like sophomore year and they just pop up out of nowhere.", False),
            ("This opening line is so corny though, read it. Hey stranger, with the winky face.", True),
            ("I don't know if I should reply, to be honest. Part of me is curious, part of me is cringing.", False),
            ("Going to leave them on read for a bit and make them sweat lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Email Inbox Zero Impossible - Drowning in Emails
    # User overwhelmed by email count showing their inbox on screen
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "email_inbox_zero",
        [
            ("I took one day off and my inbox literally imploded. I can't do this anymore.", False),
            ("Check this out, 847 unread emails. How is that even possible in 24 hours?", True),
            ("Half of them are reply-all chains that have nothing to do with me, honestly.", False),
            ("This one from HR looks important though, see the subject line.", True),
            ("I tried doing inbox zero once and gave up after like twenty minutes lol.", False),
            ("Look at all these newsletter subscriptions I never signed up for, I swear to God.", True),
            ("Going to just select all and mark as read at this point. Email is a broken system.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: WhatsApp Family Group Chaos - Endless Forwarded Messages
    # User annoyed by nonstop family group chat forwards and memes
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "whatsapp_family_group",
        [
            ("My family WhatsApp group is genuinely the most unhinged place on the internet.", False),
            ("Look at what my uncle just forwarded this morning. It's a chain message from 2012.", True),
            ("This good morning image with the roses and sparkles, I literally cannot.", True),
            ("My aunt sends like forty of these a day and nobody has the heart to say stop.", False),
            ("See this message from my mom asking why I don't reply more? Guilt trip central.", True),
            ("I muted the group for a year last time and they still didn't notice lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Discord Server Notifications - Too Many Pings
    # User overwhelmed by Discord pings and server activity
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "discord_notification_spam",
        [
            ("I stepped away from my PC for like an hour and Discord had a whole meltdown.", False),
            ("Look at this notification count, it's literally 300+ mentions. What happened?", True),
            ("Someone pinged @everyone three times for a meme that's not even funny.", False),
            ("This channel right here is where it all went down, apparently.", True),
            ("I used to love that server but lately it's just nonstop chaos every single day.", False),
            ("I'm about to mute every single server. I don't even care anymore, to be honest.", False),
            ("Wait, check this ping though. Someone actually needs help with something legit.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Slack After-Hours Message From Boss
    # User stressed about a late night Slack message from their manager
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "slack_afterhours_boss",
        [
            ("It's literally 11pm and my boss just sent me a Slack message. I'm panicking.", False),
            ("Look at this notification, it just says hey can we talk tomorrow, with no context.", True),
            ("Whenever someone says can we talk with no details, my anxiety goes through the roof.", False),
            ("This was sent at 10:58pm too, like why are you even online right now? Go to sleep.", True),
            ("Should I respond now or pretend I didn't see it until morning? I don't know what to do.", False),
            ("I already read it though. See the little eyes emoji? That means they know I saw it.", True),
            ("I'm going to be up all night overthinking this, for real. Work-life balance is dead.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Wrong Number Text Exchange - Hilarious Mix-Up
    # User showing a funny wrong number conversation on their phone
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "wrong_number_exchange",
        [
            ("The funniest thing just happened. Some random person texted me thinking I'm their dentist.", False),
            ("Look at this first message, they said hi Dr. Chen, I'm confirming my 3pm appointment.", True),
            ("I played along for a bit, which was probably wrong, but it was so funny.", False),
            ("See this part where I said your teeth look great in the x-rays? They believed it.", True),
            ("This response right here is what sent me though. They said thank you so much, doctor.", True),
            ("I eventually told them wrong number and they were so embarrassed, poor thing.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Group Chat Blowing Up - Can't Keep Up
    # User unable to keep up with a rapidly moving group chat
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "group_chat_blowup",
        [
            ("I put my phone down for fifteen minutes and the group chat has 200 new messages.", False),
            ("This conversation moved so fast, I don't know what's even happening anymore.", True),
            ("Apparently someone said something wild and everyone went off about it.", False),
            ("Look at how many people are typing right now, it's like six people at once.", True),
            ("I tried scrolling back to find where the drama started but it's impossible.", False),
            ("This message right here seems like where it all kicked off, but I'm not sure.", True),
            ("Honestly might just ask someone to give me the summary because I can't keep up lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Text Message Auto-Correct Disaster
    # User showing embarrassing autocorrect fails in their texts
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "autocorrect_disaster",
        [
            ("Autocorrect just ruined my life for the third time this week. I'm done.", False),
            ("Look at what it changed my message to. I wanted to say I'll be there soon.", True),
            ("This is so embarrassing. I sent it to my professor too, not even a friend.", True),
            ("I tried to type assessment and it corrected it to something absolutely unhinged.", False),
            ("See this text right here? That's what my phone decided I meant to say.", True),
            ("Not going to lie, I need to just turn off autocorrect entirely. It's doing more harm than good.", False),
            ("They left me on read after that, so that's cool. I guess my life is over.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Notification Overload - Phone Won't Stop Buzzing
    # User showing their notification shade absolutely flooded
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "notification_overload",
        [
            ("My phone has been vibrating nonstop for the past hour. I want to throw it away.", False),
            ("Look at this notification panel, it's literally stacked to infinity.", True),
            ("There's like eight different apps all going off at the same time right now.", False),
            ("I really need to do a full app purge this weekend and uninstall half this stuff.", False),
            ("This notification right here has been popping up every five minutes and it won't stop.", True),
            ("I'm about to turn on do not disturb and disappear from society permanently.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Ghosting Situation - Analyzing Message Timestamps
    # User forensically examining message patterns to figure out if they're being ghosted
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "ghosting_timestamp_analysis",
        [
            ("Okay so I need to show you something because I think I'm being ghosted.", False),
            ("Look at the time between these messages. I replied in two minutes, they took nine hours.", True),
            ("See how their responses keep getting shorter too? Went from paragraphs to one word.", True),
            ("They used to text me first every morning and that stopped like a week ago.", False),
            ("The worst part is I really liked this person and now it's just fading away.", False),
            ("Maybe I'm reading too much into it, but not going to lie, the pattern is right there.", False),
            ("Check this though, they were active on Instagram twenty minutes ago but can't text me back.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: iMessage Reactions vs Android - Green Bubble Drama
    # User frustrated about cross-platform messaging issues
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "green_bubble_drama",
        [
            ("The green bubble discrimination in our group chat is getting out of hand, for real.", False),
            ("Look at this message where it says Kyle laughed at an image. Like thanks, very helpful.", True),
            ("The whole iMessage vs Android thing is so dumb. Apple just needs to support RCS already.", False),
            ("All the reactions show up as separate texts and it clogs up the whole conversation.", False),
            ("See how blurry this video looks? That's because it got compressed for the green bubble.", True),
            ("Someone suggested we all switch to WhatsApp but nobody wants to download another app.", False),
            ("Lowkey feel bad for Kyle though. It's not his fault his phone ruins everything lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: WhatsApp Voice Note Overload - 5 Min Voice Notes
    # User dreading excessively long voice messages from someone
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "voice_note_overload",
        [
            ("My friend only communicates through five minute voice notes and I can't take it anymore.", False),
            ("Look at this chat, it's literally just a wall of blue voice message bubbles.", True),
            ("She sent seven in a row without waiting for me to respond to a single one.", False),
            ("This one right here is four minutes and thirty two seconds for what could be a text.", True),
            ("I don't have time to listen to a whole podcast every time she has a thought, to be honest.", False),
            ("See the timestamps? She sent all of these within like ten minutes straight.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Discord Server Drama - Mod Abuse and Role Disputes
    # User showing evidence of mod power tripping in a Discord server
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "discord_mod_drama",
        [
            ("The mods in this server are on a whole power trip right now and everyone is fed up.", False),
            ("Look at this, they literally banned someone for posting a meme in general.", True),
            ("This screenshot shows the mod saying my server my rules. Like okay, dictator.", True),
            ("Half the regulars already left because of stuff like this. It's been going downhill.", False),
            ("See this role change right here? They demoted someone just for disagreeing with them.", True),
            ("People are talking about making a new server without the toxic mods, honestly.", False),
            ("Honestly, Discord mods having unchecked power is a tale as old as time lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Email Scam Phishing Attempt - Suspicious Message Received
    # User showing a sketchy email and trying to figure out if it's legit
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "email_phishing_attempt",
        [
            ("I just got the sketchiest email ever and I need someone to tell me this is fake.", False),
            ("Look at this subject line, it says your account has been compromised, act now.", True),
            ("The sender address looks off too. See, it says support at arnazon with an r n, not m.", True),
            ("They want me to click a link and enter my password, which screams scam, right?", False),
            ("This part right here where they say dear valued customer is such a red flag, not going to lie.", True),
            ("My mom almost fell for one of these last month and I had to explain phishing to her.", False),
            ("I'm reporting this and blocking the sender, but I swear to God these scams are getting better.", False),
        ],
    ),
]

__all__ = ["TOOL_MESSAGES"]

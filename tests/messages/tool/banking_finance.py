"""Banking and finance scenarios: Venmo requests, suspicious charges, crypto, budgeting, subscriptions."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Venmo Request Drama - Someone Won't Pay Back
    # User venting about a friend dodging a Venmo request for weeks
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "venmo_request_drama",
        [
            ("Bro, I sent a Venmo request like two weeks ago and she still hasn't paid me back.", False),
            ("I literally covered her entire dinner that night and she said she'd pay me the next day.", False),
            ("Look at the timestamp on this request, it's been 14 days.", True),
            ("She keeps posting stories of her shopping hauls though, like girl you owe me 47 dollars.", False),
            (
                "Not going to lie, I'm about to just charge it again because maybe she didn't see it, I don't know.",
                False,
            ),
            ("Wait, she declined it? Check this out, she actually hit decline.", True),
            ("I'm so done lending people money, for real. This is the last time.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Suspicious Bank Charge - Unknown Transaction Appeared
    # User discovers a weird charge on their bank statement and panics
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "suspicious_bank_charge",
        [
            ("Okay, what the hell is this charge for 89.99 from some company I've never heard of?", True),
            ("I definitely did not buy anything from whatever DGTL MKTPLC LLC is.", False),
            ("See right here, it posted yesterday at 3am, which is suspicious because I was asleep.", True),
            ("I already called the bank and they're investigating it, but still, this is stressful.", False),
            ("This is the second time something weird showed up on my account this year.", False),
            ("I'm going to have to get a whole new card again, ugh.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Crypto Portfolio Check - Gains or Losses Reaction
    # User obsessively checking crypto prices and reacting to the chart
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "crypto_portfolio_check",
        [
            ("Just opened Coinbase and I think I'm going to throw up lmao.", False),
            ("Look at this chart, bro. It's literally a cliff.", True),
            ("I bought ETH at like 3800 and this number right here is making me want to cry.", False),
            ("My whole portfolio is down 40 percent since last month. I can't even look at it.", False),
            ("Wait, hold on. This one altcoin is actually pumping though, see this green candle.", True),
            ("Should've just put everything in a savings account like my dad told me to, to be honest.", False),
            ("This 24 hour graph is pure chaos, not going to lie.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Budget App Reality Check - Spending Breakdown Shock
    # User opens their budget app and is horrified by their own spending habits
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "budget_app_reality_check",
        [
            ("So I finally opened my budget app after ignoring it for a month, and wow.", False),
            ("This pie chart is actually embarrassing, like look at how big the food section is.", True),
            ("I spent 620 dollars on DoorDash alone last month. That's literally insane.", False),
            ("And see this category that says entertainment? That's all concert tickets.", True),
            ("I told myself I'd keep eating out under 200 a month and that did not happen, clearly.", False),
            ("This bar graph comparing January to February is so depressing, not going to lie.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Splitwise Group Trip Settling Up
    # Friends trying to figure out who owes what after a group vacation
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "splitwise_group_trip",
        [
            ("Okay everyone, the Splitwise for the cabin trip is finalized, so let's settle up.", False),
            ("Look at this breakdown. It shows exactly who owes who.", True),
            ("Jake, you owe me 127 and Sarah owes you like 45, so it kind of cancels out a bit.", False),
            ("Wait, this expense right here, I don't think that's right. I didn't eat at that restaurant.", True),
            ("Can someone fix that because it's throwing off my total and I don't want to overpay?", False),
            ("See this total at the bottom? That's after I already paid for the Airbnb deposit.", True),
            (
                "Just Venmo me whenever y'all can. I'm not trying to be weird about it, but also please pay me lol.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Subscription Audit - Discovering Forgotten Subscriptions
    # User goes through bank statements and finds subscriptions they forgot about
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "subscription_audit",
        [
            ("Doing a subscription audit right now because I'm hemorrhaging money apparently.", False),
            ("What is this 14.99 charge every month? I literally don't even know what this app is.", True),
            ("I cancelled that streaming service like three months ago, or at least I thought I did.", False),
            ("This one right here is a gym membership I've used exactly twice since signing up.", True),
            ("Bruh, look at all these recurring charges. It's like death by a thousand cuts.", True),
            ("I'm paying for three different cloud storage services somehow? That's so dumb.", False),
            ("This total at the bottom is over 200 a month in subscriptions alone, I swear to God.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Paycheck Direct Deposit - Excitement Then Disappointment
    # User checks their bank account on payday and reacts to the amount
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "paycheck_direct_deposit",
        [
            ("PAYDAY, LET'S GOOO! I have been waiting for this all week.", False),
            ("Wait, hold on, let me check if it actually hit yet.", False),
            ("Okay, the deposit amount is... not what I expected, to be honest.", False),
            ("Taxes took SO much out of this check, like look at the difference between gross and net.", True),
            ("I made 3200 before taxes and somehow ended up with this sad little number.", False),
            ("Half of this is going to be gone after rent hits tomorrow anyway.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Credit Card Statement Review - Where Did The Money Go
    # User scrolling through their credit card statement in disbelief
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "credit_card_statement_review",
        [
            ("Going through my credit card statement and questioning every life choice I've made.", False),
            ("That Target charge was supposed to be a quick run for toothpaste and it was 87 dollars lmao.", False),
            ("I don't even remember half of these transactions, honestly.", False),
            ("See this one from last Tuesday? I have zero memory of that purchase.", True),
            ("The interest charges at the bottom are what really hurts though. Look at this fee.", True),
            (
                "I'm going to start paying cash for everything because clearly I can't be trusted with a credit card.",
                False,
            ),
            ("This running total on the right side just keeps climbing and climbing.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Venmo Public Feed Awkwardness - Seeing Others' Transactions
    # User scrolling through the Venmo public feed and commenting on what they see
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "venmo_public_feed",
        [
            ("Why do people leave their Venmo transactions on public? This is so entertaining.", False),
            ("Look at this one. Some dude just paid his ex with the memo that says sorry.", True),
            ("This couple has been sending each other one dollar with passive aggressive emojis all day.", False),
            ("Someone from my high school just paid for something called party supplies at 2am lol. Okay.", False),
            ("Check this out. My coworker just sent her boyfriend money with like five heart emojis.", True),
            ("I need to make sure mine is on private because this feed is basically gossip fuel.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Investment App Panic - Stock Market Drops
    # User watching their investments tank in real time on the app
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "investment_app_panic",
        [
            ("The market is crashing right now and I can't stop refreshing Robinhood. Someone help me.", False),
            ("The red line is going straight down and it's giving me actual anxiety.", False),
            ("I lost 800 dollars today alone. Like, that's a whole month's rent gone.", False),
            ("Look at this ticker. Everything in my portfolio is red, not a single green.", True),
            ("Everyone on Twitter is saying buy the dip, but with what money lmao.", False),
            ("This percentage drop right here hasn't been this bad since March 2020, apparently.", True),
            ("I'm just going to close the app and pretend I didn't see any of that, to be honest.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Mobile Banking App Glitch - Balance Looks Wrong
    # User sees a weird balance in their banking app and freaks out
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "banking_app_glitch",
        [
            ("Uhhh, my bank app is showing a balance of negative 2000 and I know that's not right.", False),
            ("See this number right here? That was 1500 this morning. I checked before work.", True),
            ("I haven't spent anything today, so this has to be a glitch or something.", False),
            ("Look, there's a pending transaction here for a charge I definitely didn't make.", True),
            ("I'm lowkey panicking right now because what if someone actually drained my account.", False),
            ("Okay, I just refreshed and this balance still looks wrong. Something is off.", True),
            ("Calling the bank first thing tomorrow because this is not okay.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Cash App Scam Attempt - Suspicious Payment Request
    # User receives a sketchy Cash App request and shows it to friends
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "cashapp_scam_attempt",
        [
            ("Some random person just sent me a Cash App request for 500 dollars out of nowhere.", False),
            ("Look at this profile pic. It's clearly fake and the username is like random numbers.", True),
            ("The memo says refund processing, which makes absolutely zero sense to me.", False),
            ("I almost tapped accept because it looked official, not going to lie. That would've been bad.", False),
            ("See how they wrote it to look like it's from Cash App support? That's so shady.", True),
            ("Just reported and blocked them, but lowkey scared they have my info somehow.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Tax Refund Tracking Obsession
    # User compulsively checking the IRS refund tracker every day
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tax_refund_tracking",
        [
            ("I have checked the IRS refund tracker every single day for the past two weeks. I'm not well.", False),
            ("This status bar hasn't moved at all since I filed. Like, it's stuck on received.", True),
            ("Everyone else already got theirs back and mine is just sitting there processing.", False),
            ("Look, it's still saying the same thing as yesterday, word for word. Nothing changed.", True),
            ("I already spent that refund money in my head, so the IRS needs to hurry up, for real.", False),
            ("The estimated date they gave me was a total lie because that was last week.", False),
            ("Going to check one more time before bed even though I know nothing has changed lol.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: BNPL Regrets - Afterpay/Klarna Payments Stacking Up
    # User realizes all their buy now pay later installments are hitting at once
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "bnpl_regrets",
        [
            ("So remember when I said Afterpay was free money? Yeah, I was wrong.", False),
            ("Look at all these installment payments due this week alone. It's five different ones.", True),
            (
                "I used Klarna for that jacket and Afterpay for those shoes, and now they're all due at the same time.",
                False,
            ),
            ("This payment schedule right here is actually terrifying when you see it all together.", True),
            ("I really said I'll just pay it in four easy payments, like four times in one month lmao.", False),
            ("See this total? That's what I owe across all my BNPL apps combined, on God.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Tip Calculator Debate - Splitting Restaurant Bill
    # Group of friends arguing over how to split the bill and tip at dinner
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "tip_calculator_debate",
        [
            (
                "Okay, we need to figure out this bill because I'm not paying for your lobster when I got a salad.",
                False,
            ),
            ("Look at the receipt. The total before tip is 247 for five people.", True),
            (
                "If we split evenly, that's like 50 each, but that's not fair because some people ordered way more.",
                False,
            ),
            ("This tip calculator app is saying 20 percent would be another 49 dollars on top.", True),
            ("Who puts 18 percent as the default tip? That's lowkey cheap, to be honest. Just do 20.", False),
            ("See these itemized prices right here? Marcus, your steak was literally half the bill.", True),
            (
                "Fine, whatever, let's just split it even. I'm too tired to do math right now. Venmo me your share.",
                False,
            ),
        ],
    ),
]

__all__ = ["DATA"]

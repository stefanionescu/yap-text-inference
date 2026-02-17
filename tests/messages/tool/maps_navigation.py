"""Maps and navigation scenarios: getting lost, ride tracking, surge pricing, parking, flights, transit."""

DATA = [
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 1: Sketchy Directions - Google Maps Leading Somewhere Wrong
    # User following GPS into a bad area and questioning the route on screen
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "google_maps_sketchy_directions",
        [
            ("Bro, Google Maps is taking me down this dirt road right now and I'm lowkey scared.", False),
            ("Like there are no streetlights and this road looks like it hasn't been paved since the 90s.", False),
            ("Wait, look at this route it wants me to go through. Does that look right to you?", True),
            ("Nah, I'm not turning there. I swear to God that looks like a horror movie set.", False),
            ("This says 12 more minutes but I don't know if I trust it anymore, to be honest.", True),
            (
                "Ok, never mind, I turned around. I'm just going to take the highway. I don't care if it's longer.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 2: Uber Wrong Direction - Driver Going the Opposite Way
    # User watching their Uber driver on the map going completely wrong
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "uber_driver_wrong_direction",
        [
            ("My Uber driver is literally going the opposite direction right now. I cannot.", False),
            ("Look at this, he just turned left when the route clearly says right.", True),
            ("Bro, this man is adding like 10 minutes to the trip for no reason.", False),
            ("See this blue line on the map? He is fully ignoring it.", True),
            ("I texted him and he left me on read lmao. Great.", False),
            ("This ETA keeps going up every time I check it, I swear to God.", True),
            ("I'm about to just cancel and walk, not going to lie. It's only 15 minutes on foot.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 3: Surge Pricing Shock - Late Night Uber Costs
    # User seeing insane surge pricing and reacting to the screen
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "surge_pricing_shock",
        [
            ("Ok so I just opened Uber to go home from the bar and I think I'm going to pass out.", False),
            ("Look at this price, bro. Forty seven dollars for a 10 minute ride.", True),
            ("This surge multiplier is actually criminal. Like 3.2x, are you kidding me?", True),
            ("Last week the same ride was like twelve bucks. This is robbery, for real.", False),
            ("Wait, check this out. Lyft is even worse somehow.", True),
            ("Guess I'm sleeping at the bar tonight lmao. Not paying that.", False),
            ("Nah but for real, Uber used to be affordable. I don't know what happened.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 4: Parking Nightmare - Can't Find a Spot Downtown
    # User circling downtown blocks and checking parking apps
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "parking_nightmare_downtown",
        [
            ("I've been driving in circles for 20 minutes trying to park downtown. I hate it here.", False),
            ("Every single garage says full and street parking is a myth at this point.", False),
            ("Wait, this app shows a spot open on 5th Street. Do you see it?", True),
            ("Never mind, someone just took it while I was driving there. Cool cool cool.", False),
            ("This garage right here says $28 an hour, which is actually unhinged.", True),
            ("I should have just taken the train, honestly. Driving downtown is never worth it.", False),
            ("Ok, finally found something three blocks away, but look at this meter rate.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 5: Flight Tracker Obsession - Watching Someone's Plane
    # User obsessively tracking a loved one's flight on an app
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "flight_tracker_obsession",
        [
            ("Ok so my mom's flight took off like an hour ago and I've been refreshing this app nonstop.", False),
            ("Look, it's right over Kansas right now. This little plane icon is so cute.", True),
            ("Wait, why did it change direction slightly? Is that normal?", False),
            ("This says estimated arrival 4:47 but it originally said 4:30, so that's concerning.", True),
            ("Not going to lie, I track every flight my family takes. I know I'm dramatic about it.", False),
            ("Oh, see this? It just hit some turbulence zone. The altitude dropped a bit.", True),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 6: Transit Route Confusion - Which Bus to Take
    # User trying to figure out public transit and staring at the route map
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "transit_route_confusion",
        [
            ("Ok, I never take the bus and I'm so lost trying to figure out which one goes to Midtown.", False),
            ("This route map looks like spaghetti. I genuinely cannot read it.", True),
            ("Wait, does the 42 or the 67 go to Central Station? I don't know which line this is.", True),
            ("Someone told me to take the green line but I don't see a green line on here at all.", False),
            ("Oh wait, is this it? This one that says express?", True),
            ("To be honest, I should've just driven, but parking is insane so here we are.", False),
            ("Ok, the app says next bus in 14 min. I'm just going to trust it and hope for the best.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 7: Road Trip GPS Argument - GPS vs Gut Feeling
    # Friends arguing in the car about whether to follow GPS or take a shortcut
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "road_trip_gps_argument",
        [
            ("Me and Jake are literally fighting in the car right now because he won't follow the GPS.", False),
            ("He swears he knows a shortcut but he said that last time and we ended up in Ohio.", False),
            ("Look at this, the GPS clearly says take the next exit but he wants to keep going straight.", True),
            ("This route saves us 45 minutes but nooo, he doesn't trust technology apparently.", True),
            ('"I grew up driving these roads, I know where I\'m going," he says. Sure, bro. Sure.', False),
            ("Update: we missed the exit and now this is rerouting us through some town I've never heard of.", False),
            ("Next road trip I'm driving. That's all I have to say.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 8: Lyft vs Uber Price Compare - Checking Both Apps
    # User flipping between Lyft and Uber trying to find the cheaper ride
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "lyft_vs_uber_price_compare",
        [
            ("Ok, I'm doing the thing where I check both Uber and Lyft before I commit to one.", False),
            ("This Uber quote is $23 for UberX, which honestly isn't terrible.", True),
            ("But check this, Lyft is $19 for the same exact ride, so that's a no brainer, right?", True),
            ("Wait, the Lyft ETA is 11 minutes though and Uber is only 4. Decisions, decisions.", False),
            ("Honestly, I switch between apps like five times a day depending on who's cheaper.", False),
            ("This Lyft driver has a 4.2 rating though. That's kind of suspicious, not going to lie.", True),
            ("Going with Uber. I'm not risking a 4.2 star experience at 1am lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 9: Google Maps ETA vs Reality - Time Estimate Lies
    # User realizing the ETA is a total fantasy compared to actual traffic
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "maps_eta_vs_reality",
        [
            ("Google Maps said 25 minutes when I left the house and now it's been 40 and I'm not even close.", False),
            ("This red line on the traffic view goes on forever, bro. Look at it.", True),
            ("It keeps recalculating too. Like first it said arrive at 6:15, now it's saying 6:48.", False),
            ("See this part right here where the highway merges? That's where everything dies.", True),
            ("Whoever decided to put two highway merges back to back deserves jail time, honestly.", False),
            ("This ETA is a whole fantasy at this point. It's just making up numbers.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 10: Airport Terminal Panic - Finding the Right Gate
    # User running through the airport trying to navigate to their gate
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "airport_terminal_panic",
        [
            ("I'm literally sprinting through the airport right now because I went to the wrong terminal.", False),
            (
                "The sign said Terminal B but my boarding pass says B2, which is apparently a whole different building.",
                False,
            ),
            ("Wait, does this map show a shortcut through here or do I have to go back outside?", True),
            ("This airport layout makes zero sense. Who designed this, honestly?", False),
            ("Ok, I found the tram thing that connects the terminals. Thank God.", False),
            ("Boarding in 8 minutes and I'm still like 10 gates away. This is fine. Everything is fine.", False),
            (
                "See this gate number? It's all the way at the end of the terminal, obviously, because why wouldn't it be.",
                True,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 11: Food Delivery Driver Tracking - Watching Them on the Map
    # User watching the delivery driver take a bizarre route to their house
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "food_delivery_tracking",
        [
            ("Why is my DoorDash driver going in the complete opposite direction of my house?", False),
            ("Look at this map. He literally just passed my street and kept going.", True),
            ("This man has been sitting at the same intersection for 4 minutes. What is he doing?", True),
            ("I just want my pad thai, bro. It's not that complicated.", False),
            ("Oh wait, now he's moving again, but this route he's taking makes no sense.", False),
            (
                "Update: he called me and asked for directions to my apartment, which is wild because the app gives them to you.",
                False,
            ),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 12: Waze vs Google Maps Debate - Which App is Better
    # Friends debating navigation apps and pulling up examples on their phones
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "waze_vs_google_maps_debate",
        [
            ("Ok, this is the hill I will die on. Waze is better than Google Maps and it's not close.", False),
            ("Waze warned me about a speed trap last week that Google Maps would have never caught.", False),
            ("But look at this Google Maps interface. It's so much cleaner and easier to read.", True),
            ("This Waze route has me going through like 6 side streets to save 2 minutes. That's crazy.", True),
            (
                "Not going to lie, the Waze community alerts are elite though. People really be reporting everything.",
                False,
            ),
            ("See this right here? Google Maps doesn't even show the construction on Oak Street.", True),
            ("Honestly, I just use whatever opens first when I get in the car lmao.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 13: Address Doesn't Exist - Maps Can't Find It
    # User trying to navigate to an address that GPS simply cannot locate
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "address_doesnt_exist_maps",
        [
            ("So the address my friend gave me literally does not exist according to Google Maps.", False),
            ("I typed it in three different ways and it keeps dropping me in the middle of a field.", False),
            ("This pin right here is where it thinks the address is, but there's nothing there.", True),
            ("She swears it's a real address, but look at this satellite view. It's just trees.", True),
            (
                "I've been driving around this neighborhood for 15 minutes and none of the house numbers make sense.",
                False,
            ),
            ("Wait, is this it? No, that says 447. I need 447B, which apparently doesn't exist to GPS.", True),
            ("Calling her right now because technology has failed me completely today.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 14: Uber Pool Nightmare - Too Many Stops
    # User regretting taking an Uber Pool and watching the detour unfold
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "uber_pool_nightmare",
        [
            ("I took an Uber Pool to save like 4 dollars and I deeply regret this decision.", False),
            ("We have picked up three extra people and this route looks like a zigzag right now.", True),
            ("This ride was supposed to be 15 minutes and the app now says 38. I'm losing my mind.", True),
            ("The guy next to me smells like he bathed in cologne and we still have two more stops.", False),
            ("Look at this, we literally just drove past my apartment to pick someone else up first.", True),
            ("Never again. I'm paying full price every single time from now on. I learned my lesson.", False),
        ],
    ),
    # ═══════════════════════════════════════════════════════════════════════════════
    # TEST 15: Walking Directions Unfamiliar City - Lost on Foot
    # User navigating on foot in a city they don't know and second-guessing the app
    # ═══════════════════════════════════════════════════════════════════════════════
    (
        "walking_directions_unfamiliar_city",
        [
            (
                "Ok so I'm in Tokyo for the first time and Google Maps walking directions are both saving and confusing me.",
                False,
            ),
            ("This says to turn right but there's like four paths branching off here. Which right?", True),
            ("I've walked past this same 7-Eleven twice now, so I'm definitely going in circles.", False),
            ("Wait, look at this. It wants me to go through what looks like someone's backyard?", True),
            ("The street names don't match what's on the signs here because everything is in kanji, obviously.", False),
            ("Not going to lie, I kind of love being lost though. This neighborhood is beautiful.", False),
            ("Oh, this is the spot right here. I can see the restaurant on the map. I'm so close.", True),
        ],
    ),
]

__all__ = ["DATA"]

"""Long conversation history fixture for warm history testing.

This module provides a realistic conversation history for testing warm history
loading and prefix caching. Assistant messages are single paragraphs without
newlines, adhering to sanitization rules.
"""

WARM_HISTORY: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "Hey, so I've been thinking about finally taking that solo trip to Japan I've been putting off for like three years now. I'm looking at late October or early November because I heard the autumn foliage is absolutely insane.",
    },
    {
        "role": "assistant",
        "content": "That's so exciting! Japan in autumn is genuinely one of the most beautiful travel experiences you can have. The momiji season when the maple leaves turn brilliant shades of red and orange is absolutely breathtaking, especially in places like Kyoto, Nikko, and the Japanese Alps.",
    },
    {
        "role": "user",
        "content": "My main concerns are that I don't speak any Japanese beyond like arigato and sumimasen, and I've never traveled alone internationally before. I'm honestly a bit nervous about the whole thing.",
    },
    {
        "role": "assistant",
        "content": "For the language barrier, honestly you'll be surprised how manageable it is. Major cities like Tokyo, Osaka, and Kyoto have extensive English signage, especially in train stations and tourist areas. Google Translate's camera feature is a lifesaver for menus and signs.",
    },
    {
        "role": "user",
        "content": "That's good to know. What about safety though? I've never done solo travel before and I'm a bit worried about that.",
    },
    {
        "role": "assistant",
        "content": "Japan is genuinely one of the safest countries in the world for solo travel. The crime rate is incredibly low, public transportation runs like clockwork, and there's a cultural emphasis on helping lost tourists. You can literally leave your wallet on a train and there's a good chance someone will turn it in.",
    },
    {
        "role": "user",
        "content": "That's really reassuring. I was also wondering about the logistics of getting around. I've heard the train system is amazing but also kind of overwhelming with so many different companies and pass options.",
    },
    {
        "role": "assistant",
        "content": "Great question! The JR Pass situation has actually changed recently since they raised prices significantly in late 2023, so it's no longer the automatic no brainer it used to be. But for most tourist routes hitting Tokyo, Kyoto, and Osaka, it still makes financial sense if you plan your activation day strategically.",
    },
    {
        "role": "user",
        "content": "I'm planning to hit Tokyo, Kyoto, maybe Osaka, and I've been reading about this place called Kanazawa that looks gorgeous. Should I just get a JR Pass?",
    },
    {
        "role": "assistant",
        "content": "For that itinerary, yes the pass still makes sense. The key is to activate your 7 day pass on the day you leave Tokyo for Kanazawa, not when you arrive. That way you cover all the expensive intercity shinkansen travel and still have days left for the Kyoto Osaka corridor.",
    },
    {
        "role": "user",
        "content": "Oh that's a really smart tip about when to activate the pass. I never would have thought of that. What about local trains in the cities though?",
    },
    {
        "role": "assistant",
        "content": "Local metro systems in Tokyo and Osaka aren't covered by the JR Pass. You'll want a Suica or Pasmo IC card for those, which you can now add directly to your iPhone wallet if you have a newer model. Just tap and go, super convenient.",
    },
    {
        "role": "user",
        "content": "Okay so switching gears a bit, I've been reading about Japanese etiquette and honestly there's so much conflicting information online. Like some sites make it seem like you'll deeply offend everyone if you don't bow at exactly the right angle.",
    },
    {
        "role": "assistant",
        "content": "The internet loves to make Japanese etiquette seem like this minefield where one wrong move means eternal shame. The reality is much more relaxed, especially for obvious tourists. Japanese people understand that foreigners come from different cultural backgrounds, and genuine politeness goes way further than perfect execution.",
    },
    {
        "role": "user",
        "content": "What are the things that actually matter though? I want to be respectful but I don't want to stress about every little thing.",
    },
    {
        "role": "assistant",
        "content": "Shoes are non negotiable. When you enter someone's home, traditional restaurants, ryokan, some temples, you remove your shoes. There will usually be a clear step up or genkan entrance area. If you see a row of slippers, that's your cue. Never wear outdoor shoes on tatami mats.",
    },
    {
        "role": "user",
        "content": "Got it, shoes off. What about chopsticks? I've heard there are a bunch of rules about those too.",
    },
    {
        "role": "assistant",
        "content": "Don't stick them upright in rice since that's associated with funeral rituals. Don't pass food chopstick to chopstick for the same reason. Don't point with them or wave them around. Other than that, nobody cares if your technique is a bit clumsy.",
    },
    {
        "role": "user",
        "content": "What about tipping? I know in the US you tip everywhere but I've heard Japan is different.",
    },
    {
        "role": "assistant",
        "content": "Just don't tip at all. It's not expected and can actually be confusing or even offensive in some contexts. Service charges are included in prices. This applies to restaurants, taxis, hotels, everywhere. It's honestly one less thing to think about.",
    },
    {
        "role": "user",
        "content": "One more thing before I start booking stuff. I'm vegetarian, not vegan but no meat or fish. I've heard mixed things about how easy or hard this is in Japan since apparently fish stock is in like everything?",
    },
    {
        "role": "assistant",
        "content": "I'll be honest, this is probably the trickiest part of your trip to navigate. Dashi, the fish and kelp stock, is in an enormous number of Japanese dishes including things that look vegetarian on the surface, like miso soup, many noodle broths, and various simmered dishes.",
    },
    {
        "role": "user",
        "content": "That sounds rough. Is there any way to make it work?",
    },
    {
        "role": "assistant",
        "content": "Tokyo in particular has seen a boom in dedicated vegetarian and vegan restaurants over the past few years. Apps like HappyCow will be your best friend. Seriously download it before you go and save restaurants near your accommodations.",
    },
    {
        "role": "user",
        "content": "Any specific types of places I should look for?",
    },
    {
        "role": "assistant",
        "content": "Shojin ryori is traditional Buddhist temple cuisine that's completely plant based by religious requirement, and it's genuinely delicious. Indian restaurants are common in Japan and obviously vegetarian friendly. Italian places usually have vegetarian pasta options too.",
    },
    {
        "role": "user",
        "content": "Alright, I'm feeling way more confident about this whole thing now. Let me ask you something completely different though. I've been getting into baking bread lately, specifically sourdough.",
    },
    {
        "role": "assistant",
        "content": "Oh nice, welcome to the sourdough rabbit hole! It's genuinely one of the most satisfying hobbies once you get the hang of it. There's something almost meditative about the whole process once you stop stressing about it.",
    },
    {
        "role": "user",
        "content": "My starter is about two months old now. I'm getting decent oven spring but my crumb is still way denser than what I see in all those Instagram photos. Any thoughts?",
    },
    {
        "role": "assistant",
        "content": "Two months is still relatively early in your journey, so don't be too hard on yourself. Those Instagram loaves are often the result of years of practice, very specific flour choices, and frankly some selective photography. Dense crumb usually comes down to a few key factors though.",
    },
    {
        "role": "user",
        "content": "What should I be looking at first?",
    },
    {
        "role": "assistant",
        "content": "First question: how's your starter behaving? At two months it should be pretty reliable, but the real test is whether it doubles consistently within 4 to 6 hours of feeding at room temperature. If it's sluggish or inconsistent, that could be affecting your final rise.",
    },
    {
        "role": "user",
        "content": "My starter is pretty active, doubles in about 5 hours. I've been doing like 4 hours of bulk at around 75 degrees Fahrenheit. Should I be going longer?",
    },
    {
        "role": "assistant",
        "content": "That timing sounds potentially on the shorter side. At 75 degrees Fahrenheit with a starter that takes 5 hours to peak, you'd probably want your bulk fermentation to be more like 5 to 7 hours depending on the dough's behavior. A lot of new bakers underproof because they're nervous about overproofing.",
    },
    {
        "role": "user",
        "content": "How do I know when the bulk is actually done though? I've been going purely by time.",
    },
    {
        "role": "assistant",
        "content": "Move away from time based baking and toward reading the dough itself. The dough should roughly increase by 50 to 75 percent, feel airier and less dense when you fold it, and you should see bubbles on the surface. When you poke it, the indent should fill back slowly over about 3 to 4 seconds.",
    },
    {
        "role": "user",
        "content": "What flour are you using? I've heard that matters a lot.",
    },
    {
        "role": "assistant",
        "content": "For open, airy crumb, you generally want higher protein bread flour, ideally 12 to 14 percent protein. King Arthur bread flour is a solid, consistent choice that's widely available. All purpose has lower protein and could definitely be contributing to density if that's what you're using.",
    },
    {
        "role": "user",
        "content": "I'm using King Arthur bread flour actually so that should be good. One thing I've been confused about is scoring. Sometimes my scores open up beautifully and other times they just seal back up.",
    },
    {
        "role": "assistant",
        "content": "Scoring is honestly one of those things that looks simple but has a lot of variables. The most common reason scores seal up is actually related to proofing. If your dough is underproofed, the surface tension is really high and the dough fights back against the blade.",
    },
    {
        "role": "user",
        "content": "Is there a technique to it though? Like blade angle or anything?",
    },
    {
        "role": "assistant",
        "content": "Blade angle matters a lot. You want to hold your lame at about 30 to 45 degrees relative to the dough surface, not straight up and down. A shallow angle creates that lip that catches the steam and curls into an ear. Also make sure your blade is genuinely sharp since dull blades drag and create ragged edges.",
    },
    {
        "role": "user",
        "content": "I've been doing cold retard overnight. Should I score before or after it warms up?",
    },
    {
        "role": "assistant",
        "content": "Score the loaf right before it goes in the oven while it's still cold. Cold dough holds its shape much better and the scores stay crisp. Scoring room temperature dough is way harder because it's soft and sticky and tends to deflate on you.",
    },
    {
        "role": "user",
        "content": "What about steam? I'm using a Dutch oven but I've seen people spraying water into their ovens too. Is there any benefit to extra steam?",
    },
    {
        "role": "assistant",
        "content": "With a Dutch oven you really don't need extra steam and I'd actually recommend against it. The whole point is that it creates a sealed environment where the moisture coming off the dough gets trapped and does all the work. Adding a spray bottle is just unnecessary complexity.",
    },
    {
        "role": "user",
        "content": "When should I take the lid off? I've been doing it at 20 minutes but I'm not sure if that's right.",
    },
    {
        "role": "assistant",
        "content": "20 minutes is pretty standard and works well for most recipes. The steam from the dough happens in the first 15 to 20 minutes when the loaf is heating up. After that you want a dry environment to develop the crust, so removing the lid then makes sense.",
    },
    {
        "role": "user",
        "content": "Any tips on getting a darker crust? Mine always comes out kind of pale even after the full bake time.",
    },
    {
        "role": "assistant",
        "content": "Try bumping up your temperature after you remove the lid. Some bakers start at 500 degrees Fahrenheit with the lid on, then drop to 450 or even 475 after removing it. The higher heat helps with browning but watch your bottom since Dutch ovens can run hot and burn the base.",
    },
]

# Follow-up messages to test recall of the conversation history
HISTORY_RECALL_MESSAGES: list[str] = [
    "Wait, what was the very first thing I told you about at the start of our conversation?",
    "Earlier you mentioned a specific tip about when to activate the JR Pass. What was that again?",
    "What did you say about tipping in Japan? I want to make sure I remember correctly.",
    "Remind me what flour brand you recommended for sourdough?",
    "You gave me a specific temperature range for bulk fermentation. What was it?",
    "What was your advice about scoring cold versus warm dough?",
]

__all__ = ["WARM_HISTORY", "HISTORY_RECALL_MESSAGES"]

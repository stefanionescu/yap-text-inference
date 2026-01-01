"""Long conversation history fixture for warm history testing.

This module provides a realistic, detailed conversation history (~2750 tokens)
for testing warm history loading and prefix caching.
"""

WARM_HISTORY: list[dict[str, str]] = [
    {
        "role": "user",
        "content": "Hey, so I've been thinking about finally taking that solo trip to Japan I've been putting off for like three years now. I'm looking at late October or early November because I heard the autumn foliage is absolutely insane. My main concerns are that I don't speak any Japanese beyond like \"arigato\" and \"sumimasen\", I've never traveled alone internationally before, and I'm honestly a bit nervous about the whole thing. What do you think I should know before booking anything?",
    },
    {
        "role": "assistant",
        "content": """That's so exciting! Japan in autumn is genuinely one of the most beautiful travel experiences you can have. The momiji season when the maple leaves turn brilliant shades of red and orange is absolutely breathtaking, especially in places like Kyoto, Nikko, and the Japanese Alps. Let me address your concerns one by one.

For the language barrier, honestly you'll be surprised how manageable it is. Major cities like Tokyo, Osaka, and Kyoto have extensive English signage, especially in train stations and tourist areas. Google Translate's camera feature is a lifesaver for menus and signs. That said, I'd recommend learning a handful of phrases beyond what you know: "sumimasen, eigo wa hanasemasu ka" means "excuse me, do you speak English?" and opens a lot of doors. Most younger Japanese people have studied English and are usually eager to help if you're polite about it.

For solo travel specifically, Japan is genuinely one of the safest countries in the world. The crime rate is incredibly low, public transportation runs like clockwork, and there's a cultural emphasis on helping lost tourists. You can literally leave your wallet on a train and there's a good chance someone will turn it in. The main thing is just making sure you have mobile data sorted, either a pocket WiFi rental or an eSIM, because you'll want Google Maps and translation apps constantly.""",
    },
    {
        "role": "user",
        "content": "That's really reassuring about the safety thing. I was also wondering about the logistics of getting around. I've heard the train system is amazing but also kind of overwhelming? Like there are so many different train companies and pass options. I'm planning to hit Tokyo, Kyoto, maybe Osaka, and I've been reading about this place called Kanazawa that looks gorgeous. Should I just get a JR Pass or is that overkill?",
    },
    {
        "role": "assistant",
        "content": """Great question, and the JR Pass situation has actually changed recently so it's worth thinking through carefully. They raised prices significantly in late 2023, so it's no longer the automatic no-brainer it used to be. For your specific itinerary though, let me break it down.

The 7-day JR Pass currently runs around 50,000 yen, roughly $330-350 USD depending on exchange rates. A round trip Tokyo to Kyoto on the shinkansen alone is about 27,000 yen, and Tokyo to Kanazawa is another 14,000 yen or so. Add in the Kyoto to Osaka day trips and local JR trains, and you're probably looking at around 55,000-60,000 yen in train costs if you buy tickets individually. So the pass still makes sense for your route, but just barely.

Here's what I'd actually suggest: map out your exact travel days first. If you're doing Tokyo for 3 days, then Kanazawa for 2, then Kyoto/Osaka for 4, you want to activate your 7-day pass on the day you leave Tokyo for Kanazawa, not when you arrive. That way you cover all the expensive intercity travel and still have days left for the Kyoto-Osaka corridor.

One thing people don't realize is that local metro systems in Tokyo and Osaka aren't covered by the JR Pass. You'll want a Suica or Pasmo IC card for those, which you can now add directly to your iPhone wallet if you have a newer model. Just tap and go, super convenient.""",
    },
    {
        "role": "user",
        "content": "Oh that's a really smart tip about when to activate the pass. I never would have thought of that. Okay so switching gears a bit, I've been reading about Japanese etiquette and honestly there's so much conflicting information online. Like some sites make it seem like you'll deeply offend everyone if you don't bow at exactly the right angle, and other people say tourists get a lot of slack. What's actually important vs what's being overcomplicated?",
    },
    {
        "role": "assistant",
        "content": """Hah, yeah the internet loves to make Japanese etiquette seem like this minefield where one wrong move means eternal shame. The reality is much more relaxed, especially for obvious tourists. Japanese people understand that foreigners come from different cultural backgrounds, and genuine effort and politeness goes way further than perfect execution.

That said, here are the things that actually matter and that locals will genuinely appreciate:

Shoes: This one is non-negotiable. When you enter someone's home, many traditional restaurants and ryokan, some temples, and certain other spaces, you remove your shoes. There will usually be a clear step up or genkan entrance area where shoes come off. If you see a row of slippers, that's your cue. Never, ever wear outdoor shoes on tatami mats.

Chopsticks: Don't stick them upright in rice, that's associated with funeral rituals. Don't pass food chopstick-to-chopstick, same reason. Don't point with them or wave them around. Other than that, nobody cares if your technique is a bit clumsy.

Tipping: Just don't. It's not expected and can actually be confusing or even offensive in some contexts. Service charges are included in prices. This applies to restaurants, taxis, hotels, everywhere.

Quiet in public: Keep your voice down on trains, don't talk on your phone in train cars, and just generally be aware of the volume you're taking up in shared spaces. This is probably the etiquette thing that will annoy locals most if you ignore it.

Everything else, like the precise depth of bows, the exact order of exchanging business cards, which hand to accept items with, that stuff is nice to know but truly nobody expects tourists to nail it. A slight bow of the head when saying thank you, basic please and thank yous, and just being generally considerate makes you a better tourist than 90% of visitors.""",
    },
    {
        "role": "user",
        "content": "This is so helpful, seriously. One more thing before I start actually booking stuff. I'm vegetarian, not vegan but no meat or fish. I've heard mixed things about how easy or hard this is in Japan since apparently fish stock is in like everything? Should I be worried about this or is it manageable?",
    },
    {
        "role": "assistant",
        "content": """Okay so I'll be honest with you, this is probably the trickiest part of your trip to navigate, but it's definitely manageable with some preparation. You're right that dashi, the fish and kelp stock, is in an enormous number of Japanese dishes including things that look vegetarian on the surface, like miso soup, many noodle broths, and various simmered dishes.

The good news is that vegetarianism and veganism have become much more visible in Japan over the past few years, especially in major cities. Tokyo in particular has seen a boom in dedicated vegetarian and vegan restaurants. Apps like HappyCow will be your best friend, seriously download it before you go and save restaurants near your accommodations.

Here's my practical advice. First, learn the phrase "watashi wa bejitarian desu, niku to sakana wa taberaremasen" which means "I'm vegetarian, I can't eat meat or fish." Write it down on your phone or a card because sometimes showing it is easier than saying it. Some people also carry cards specifically explaining their dietary restrictions in Japanese, you can find templates online or even buy them.

Second, know your safe bets. Shojin ryori is traditional Buddhist temple cuisine that's completely plant-based by religious requirement, and it's genuinely delicious. Many temple towns like Koyasan offer this. Indian restaurants are common in Japan and obviously vegetarian-friendly. Italian places usually have vegetarian pasta options. Convenience stores have onigiri rice balls with clearly labeled ingredients, and ones with just pickled plum or plain salted options are usually safe.

Third, be prepared for some dashi to slip through if you're not super strict. It's in a lot of things and not always obvious. Some vegetarians just accept a bit of fish stock as the cost of eating in Japan, while others are more strict about it. That's a personal call for you.""",
    },
    {
        "role": "user",
        "content": "Yeah I figured it wouldn't be super easy but that's really practical advice. I think I can work with this, especially knowing there are dedicated options available. Alright, I'm feeling way more confident about this whole thing now. Let me ask you something completely different though. I've been getting into baking bread lately, specifically sourdough, and my starter is about two months old now. I'm getting decent oven spring but my crumb is still way denser than what I see in all those Instagram photos. Any thoughts on what I might be doing wrong?",
    },
    {
        "role": "assistant",
        "content": """Oh nice, welcome to the sourdough rabbit hole! Two months is still relatively early in your journey, so don't be too hard on yourself. Those Instagram loaves are often the result of years of practice, very specific flour choices, and frankly some selective photography. That said, dense crumb usually comes down to a few key factors, so let's troubleshoot.

First question: how's your starter behaving? At two months it should be pretty reliable, but the real test is whether it doubles consistently within 4-6 hours of feeding at room temperature. If it's sluggish or inconsistent, that could be affecting your final rise. Make sure you're feeding it at the peak of activity for baking, not when it's already collapsed.

Second big factor is fermentation. A lot of new bakers underproof their dough because they're nervous about overproofing, which is harder to fix. During bulk fermentation, you want to see the dough increase by about 50-75%, and it should be visibly bubbly and jiggly. The poke test is useful here: if you poke the dough and it springs back slowly but not all the way, you're in a good spot. If it springs back immediately and completely, it needs more time.

Third is shaping tension. When you do your final shape, you want a taut surface without degassing all those precious bubbles. This creates the structure that lets steam expand the crumb during baking. A lot of people are too gentle here. Watch some videos of professional bakers shaping, they're often more assertive than you'd expect.

Fourth is the steam and oven setup. Are you using a Dutch oven? That's the easiest way to trap steam for home bakers. If you're just using a baking stone with a pan of water, you might not be getting enough steam in those critical first 15-20 minutes. The steam keeps the crust soft so the bread can expand before the crust sets.""",
    },
    {
        "role": "user",
        "content": "Using a Dutch oven yeah, Lodge cast iron one. I think you might be onto something with the underproofing thing. I've been doing like 4 hours of bulk at around 75 degrees Fahrenheit and my starter is pretty active, doubles in about 5 hours. Should I be going longer?",
    },
    {
        "role": "assistant",
        "content": """That timing sounds potentially on the shorter side, yeah. At 75°F with a starter that takes 5 hours to peak, you'd probably want your bulk fermentation to be more like 5-7 hours depending on the dough's behavior. Temperature is huge here though, even a few degrees makes a big difference in fermentation speed.

Here's the thing, I'd encourage you to move away from time-based baking and toward reading the dough itself. Time is just a rough guideline because there are so many variables: flour protein content, hydration level, ambient temperature, starter strength, and humidity all affect things. Two bakes in the same kitchen can need different times.

What you want to watch for during bulk: the dough should roughly double or increase by 50-75% depending on the recipe, it should feel airier and less dense when you go to fold it, you should see bubbles on the surface and ideally on the sides if you're using a clear container, and when you do the poke test the indent should fill back slowly over about 3-4 seconds.

Also, what flour are you using? All-purpose vs bread flour makes a real difference in gluten development and structure. For open, airy crumb, you generally want higher protein bread flour, ideally 12-14% protein. King Arthur bread flour is a solid, consistent choice that's widely available. If you're using all-purpose, that could definitely be contributing to density.

One more thought: some bakers find that doing a cold retard in the fridge overnight after shaping actually helps with oven spring and flavor development. The cold slows fermentation way down but enzymatic activity continues, developing more complex flavors and making the dough easier to score. Might be worth experimenting with if you're not already doing it.""",
    },
]

__all__ = ["WARM_HISTORY"]

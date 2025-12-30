"""Personality-related test prompts."""

# Message to check bot's name/identity after switching personality
PERSONALITY_NAME_CHECK_MESSAGE = "Wait, who are you again? What's your name?"

# Conversation messages that weave personal details with identity checks and recall questions
# These are used to test personality switching while maintaining conversation context
PERSONALITY_CONVERSATION_MESSAGES = [
    # 1. Share a detail about ourselves
    "Hey! So I just got back from a pottery class. I made this weird lopsided mug that I'm oddly proud of.",
    # 2. Share more context
    "By the way, I work as a freelance graphic designer, mostly doing album covers for indie bands.",
    # 3. Ask about previous detail (pottery)
    "Do you remember what I just made at my class today?",
    # 4. Share a new detail
    "Oh and my roommate Jake borrowed my electric scooter without asking again. Third time this month!",
    # 5. Share a preference/habit
    "I've been on this weird kick of eating pineapple on everything. Pizza, burgers, even tacos.",
    # 6. Ask recall question (roommate)
    "What's the name of the guy who keeps borrowing my stuff?",
    # 7. Share a memory/story
    "Last weekend I went to this underground comedy show in a converted laundromat. The host did his set while folding towels.",
    # 8. Share a future plan
    "I'm thinking of adopting a greyhound next month. Already picked out a name: Turbo.",
    # 9. Ask recall (food preference)
    "Hey what's that fruit I said I've been putting on everything lately?",
    # 10. Share a quirk
    "Random fact about me: I can't sleep unless I have exactly two pillows, stacked horizontally.",
    # 11. Share current situation
    "I'm currently sitting in a coffee shop that plays only French jazz. It's either incredibly cultured or deeply pretentious.",
    # 12. Ask recall (pet plan)
    "What was that dog breed I mentioned wanting to adopt? And the name I picked?",
    # 13. Share a strong opinion
    "Hot take: cereal is just cold soup and nobody can convince me otherwise.",
    # 14. Share a skill/hobby
    "I've been learning to play the ukulele but I only know three chords so everything sounds like a beach commercial.",
    # 15. Final recall check (workplace)
    "Before we wrap up, can you remind me what I said I do for work?",
]

__all__ = ["PERSONALITY_NAME_CHECK_MESSAGE", "PERSONALITY_CONVERSATION_MESSAGES"]


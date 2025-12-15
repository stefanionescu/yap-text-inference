"""Generation/tuning parameter defaults for test CLIs."""

DEFAULT_TRIM_SILENCE = "false"

TEMPERATURE_RANGE = (0.3, 0.9)
TEMPERATURE_HELP = (
    f"Temperature for generation ({TEMPERATURE_RANGE[0]}-{TEMPERATURE_RANGE[1]}). "
    "If not specified, uses voice default"
)

TOP_P_RANGE = (0.7, 1.0)
TOP_P_HELP = f"Top-p for generation ({TOP_P_RANGE[0]}-{TOP_P_RANGE[1]}). " "If not specified, uses voice default"

REPETITION_PENALTY_RANGE = (1.1, 1.9)
REPETITION_PENALTY_HELP = (
    "Repetition penalty for generation "
    f"({REPETITION_PENALTY_RANGE[0]}-{REPETITION_PENALTY_RANGE[1]}). "
    "If not specified, uses voice default"
)

PRESPEECH_PAD_MS_RANGE = (50.0, 700.0)
PRESPEECH_PAD_MS_HELP = (
    "Pre-speech pad in ms when trimming "
    f"({int(PRESPEECH_PAD_MS_RANGE[0])}-{int(PRESPEECH_PAD_MS_RANGE[1])}). "
    "Omit to use server default"
)

import os
import re
from dataclasses import dataclass


def _remove_wink_patterns(text: str) -> str:
    text = re.sub(r"\s*wink\s*wink\s*", " ", text, flags=re.IGNORECASE)
    text = re.sub(r" {2,}", " ", text)
    return text


def _fix_streaming_punctuation(text: str) -> str:
    return re.sub(r"([a-z])\s{2,}([A-Z])", r"\1. \2", text)


def _convert_math_to_words(text: str) -> str:
    text = text.replace('+', ' plus ').replace('-', ' minus ').replace('*', ' multiplied by ').replace('/', ' divided by ').replace('=', ' equals ')
    text = _convert_time_to_words(text)
    text = re.sub(r" {2,}", " ", text)
    if len(text.strip()) > 2:
        text = text.strip()
    return text


def _convert_standalone_math_to_words(text: str) -> str:
    pattern = r"\b\d+\s*[+\-*/=]\s*[\d+\-*/=\s]+\b"
    def repl(m):
        return _convert_math_to_words(m.group(0)) + " "
    return re.sub(pattern, repl, text)


def _convert_time_to_words(text: str) -> str:
    number_words = {
        0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
        6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
        11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen", 15: "fifteen",
        16: "sixteen", 17: "seventeen", 18: "eighteen", 19: "nineteen", 20: "twenty",
        21: "twenty one", 22: "twenty two", 23: "twenty three", 24: "twenty four",
        25: "twenty five", 26: "twenty six", 27: "twenty seven", 28: "twenty eight",
        29: "twenty nine", 30: "thirty", 31: "thirty one", 32: "thirty two",
        33: "thirty three", 34: "thirty four", 35: "thirty five", 36: "thirty six",
        37: "thirty seven", 38: "thirty eight", 39: "thirty nine", 40: "forty",
        41: "forty one", 42: "forty two", 43: "forty three", 44: "forty four",
        45: "forty five", 46: "forty six", 47: "forty seven", 48: "forty eight",
        49: "forty nine", 50: "fifty", 51: "fifty one", 52: "fifty two",
        53: "fifty three", 54: "fifty four", 55: "fifty five", 56: "fifty six",
        57: "fifty seven", 58: "fifty eight", 59: "fifty nine", 60: "sixty",
        61: "sixty one", 62: "sixty two", 63: "sixty three", 64: "sixty four",
        65: "sixty five", 66: "sixty six", 67: "sixty seven", 68: "sixty eight",
        69: "sixty nine", 70: "seventy", 71: "seventy one", 72: "seventy two",
        73: "seventy three", 74: "seventy four", 75: "seventy five", 76: "seventy six",
        77: "seventy seven", 78: "seventy eight", 79: "seventy nine", 80: "eighty",
        81: "eighty one", 82: "eighty two", 83: "eighty three", 84: "eighty four",
        85: "eighty five", 86: "eighty six", 87: "eighty seven", 88: "eighty eight",
        89: "eighty nine", 90: "ninety", 91: "ninety one", 92: "ninety two",
        93: "ninety three", 94: "ninety four", 95: "ninety five", 96: "ninety six",
        97: "ninety seven", 98: "ninety eight", 99: "ninety nine"
    }

    def conv(num_str: str) -> str:
        try:
            num = int(num_str)
        except ValueError:
            return num_str
        if num < 100:
            return number_words.get(num, num_str)
        if num < 1000:
            hundreds = num // 100
            rem = num % 100
            res = number_words[hundreds] + " hundred"
            if rem > 0:
                res += " " + number_words.get(rem, str(rem))
            return res
        return str(num)

    def repl_ext(m):
        parts = re.split(r"[:-]", m.group(0))
        return ", ".join(conv(p) if p.isdigit() else p for p in parts)

    def repl_basic(m):
        return f"{conv(m.group(1))}, {conv(m.group(2))}"

    text = re.sub(r"\d{1,2}(?:[:-]\d{1,2})+", repl_ext, text)
    text = re.sub(r"(\d{1,2}):(\d{1,2})(?![:-])", repl_basic, text)

    def repl_standalone(m):
        num = m.group(0)
        start, end = m.span()
        prev = text[start - 1] if start > 0 else ' '
        nxt = text[end] if end < len(text) else ' '
        if prev.isdigit() or nxt.isdigit():
            return num
        if nxt.isalpha() or nxt in '.!?,:;':
            return conv(num)
        return num

    return re.sub(r"\b\d+\b", repl_standalone, text)


def _apply_stream_replacements(text: str, convert_numbers: bool) -> str:
    text = text.replace('@', 'at')
    text = text.replace('fking', 'fucking')
    text = text.replace('"', "'")
    text = text.replace('%', ' percent')
    text = text.replace('\t', ' ')
    text = re.sub(r' {2,}', ' ', text)
    text = text.replace(' ;)', '')
    text = _remove_wink_patterns(text)
    text = _fix_streaming_punctuation(text)
    if '(' in text and ')' in text:
        # math and parentheses
        text = re.sub(r'\(([^)]+)\)', lambda m: '' if re.match(r'^\s*\d+\s*$', m.group(1)) else ('(' + _convert_math_to_words(m.group(1)) + ')' if re.search(r'[+\-*/=]', m.group(1)) else m.group(0)), text)
        text = _convert_standalone_math_to_words(text)
        text = re.sub(r' {2,}', ' ', text)
        if len(text.strip()) > 2:
            text = text.strip()
    if convert_numbers:
        text = _convert_time_to_words(text)
    if '  ' in text:
        text = re.sub(r' {2,}', ' ', text)
    return text


def _remove_emojis(text: str) -> str:
    return re.sub(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\U00002700-\U000027BF\U0001F900-\U0001F9FF\U0001F018-\U0001F270\U0001F000-\U0001F02F]', '', text)


def _normalize_whitespace(text: str) -> str:
    text = re.sub(r'\s*\n+\s*', ' ', text)
    text = re.sub(r' {2,}', ' ', text)
    return text


def ensure_proper_ending_punctuation(text: str) -> str:
    if not text or not text.strip():
        return text
    trimmed = text.rstrip()
    if not trimmed:
        return text
    if trimmed[-1] in '.!?…':
        return text
    return trimmed + '.'


@dataclass
class StreamCleaner:
    remove_emojis: bool = bool(int(os.getenv('TEXTPROC_REMOVE_EMOJIS', '1')))
    convert_numbers: bool = bool(int(os.getenv('TEXTPROC_CONVERT_NUMBERS', '0')))

    def clean_increment(self, full_text: str) -> str:
        text = _apply_stream_replacements(full_text, self.convert_numbers)
        if self.remove_emojis:
            text = _remove_emojis(text)
        text = _normalize_whitespace(text)
        return text



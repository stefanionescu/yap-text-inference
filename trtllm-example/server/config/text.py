from __future__ import annotations

# Language-specific abbreviations intended for sentence splitting logic.

# English abbreviations (no trailing dots in canonical form)
ABBREVIATIONS_EN: set[str] = {
    "mr",
    "mrs",
    "ms",
    "dr",
    "prof",
    "sr",
    "jr",
    "vs",
    "st",
    "no",
    "inc",
    "ltd",
    "etc",
    "e.g",
    "i.e",
    "al",
    "fig",
    "dept",
    "est",
    "col",
    "gen",
    "cmdr",
    "u.s",
    "u.k",
    "u.n",
    "a.m",
    "p.m",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
}

# French abbreviations
ABBREVIATIONS_FR: set[str] = {
    "m",
    "mme",
    "mlle",
    "dr",
    "prof",
    "st",
    "ste",
    "no",
    "etc",
    "cf",
    "ex",
    "janv",
    "févr",
    "mars",
    "avr",
    "mai",
    "juin",
    "juil",
    "août",
    "sept",
    "oct",
    "nov",
    "déc",
    "p.ex",
    "c.-à-d",
    "n°",
    "p.",
    "pp.",
}

# Language mapping
ABBREVIATIONS: dict[str, set[str]] = {
    "en": ABBREVIATIONS_EN,
    "fr": ABBREVIATIONS_FR,
}

__all__ = ["ABBREVIATIONS_EN", "ABBREVIATIONS_FR", "ABBREVIATIONS"]

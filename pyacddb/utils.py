replacement_dict = {
    "\u00e4": "ä",
    "\u00f6": "ö",
    "\u00fc": "ü",
    "\u00c4": "Ä",
    "\u00d6": "Ö",
    "\u00dc": "Ü",
    "\u00df": "ß",
}


def strip(text: str) -> str:
    for escape_sequence, char in replacement_dict.items():
        text = text.replace(escape_sequence, char)

    return text

import re
from typing import List, Tuple


def standardize_quotes(text: str) -> str:
    """
    Replace various opening and closing quote marks with standard ASCII double quotes.

    Args:
        text (str): The input text containing various types of quotes.

    Returns:
        str: The text with all quotes standardized to ASCII double quotes.
    """
    # Replace non-standard opening quotes with ASCII double quotes
    text = re.sub(r"[“„]", '"', text)
    # Replace non-standard closing quotes with ASCII double quotes
    text = re.sub(r"[”]", '"', text)
    return text


class Query:

    def __init__(self, tags, caption, start_date, end_date):
        self.tags = tags
        self.caption = caption
        self.start_date = start_date
        self.end_date = end_date


def parse_blocks(message: str) -> Tuple[List[str], str]:
    """
    Parse a message into a list of tags and optionally a caption and a date.
    Handling both quoted and unquoted tags.
    Quoted tags can include spaces, and all quotes are standardized before parsing.

    Args:
        message (str): The input message containing tags, potentially quoted.

    Returns:
        List[str]: A list of tags extracted from the message.
        str: The caption to search for. Might be '' if no caption was detected.
    """
    # Standardize quotes in the message first
    message = standardize_quotes(message)

    # Regular expression to match quoted text or words
    matches = re.findall(r'"([^"]+)"|(\S+)', message)

    # Each match is a tuple with the quoted text in the first position (if present)
    # and the unquoted text in the second position. We join these and filter out empty strings.
    blocks = [quoted or unquoted for quoted, unquoted in matches]

    # Initialize variables
    caption = ""
    start_date, end_date = None, None
    i = 0
    tags = []

    while i < len(blocks):
        block = blocks[i]
        print(i, block)
        if block.startswith('"') and block.endswith('"'):
            block = block[1:-1]  # Remove the surrounding quotes

        if block.startswith("cap:"):
            i += 1
            caption_parts = []
            while i < len(blocks) and not blocks[i].startswith("date:"):
                caption_parts.append(blocks[i].strip('"'))
                i += 1
            caption = " ".join(caption_parts)
            continue

        elif block.startswith("date:"):
            i += 1
            if i < len(blocks) and "-" in blocks[i]:
                date_parts = blocks[i].split("-")
                start_date = date_parts[0]
                end_date = date_parts[1] if len(date_parts) > 1 else start_date

            i += 1
            continue

        else:
            tags.append(block)

        i += 1

    # Ensure start_date is always less than or equal to end_date
    if start_date and end_date and start_date > end_date:
        start_date, end_date = end_date, start_date

    query = Query(tags, caption, start_date, end_date)
    return query

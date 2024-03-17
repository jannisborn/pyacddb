import re
from typing import List


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


def parse_tags(message: str) -> List[str]:
    """
    Parse a message into a list of tags, handling both quoted and unquoted tags.
    Quoted tags can include spaces, and all quotes are standardized before parsing.

    Args:
        message (str): The input message containing tags, potentially quoted.

    Returns:
        List[str]: A list of tags extracted from the message.
    """
    # Standardize quotes in the message first
    message = standardize_quotes(message)

    # Regular expression to match quoted text or words
    pattern = r'"([^"]+)"|(\S+)'
    matches = re.findall(pattern, message)

    # Each match is a tuple with the quoted text in the first position (if present)
    # and the unquoted text in the second position. We join these and filter out empty strings.
    tags = [quoted or unquoted for quoted, unquoted in matches]

    return tags

import pytest

from ..utils import parse_blocks


# Fixture to create a standard message structure for testing
@pytest.fixture
def standard_message():
    return 'hiking "New York" climbing'


def test_basic_tags(standard_message):
    query = parse_blocks(standard_message)
    assert query.tags == ["hiking", "New York", "climbing"]
    assert query.caption == ""
    assert query.start_date is None
    assert query.end_date is None


def test_caption_extraction():
    message = 'hiking "New York" cap: A lovely day out on the trails'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == "A lovely day out on the trails"
    assert query.start_date is None
    assert query.end_date is None


def test_date_extraction():
    message = 'hiking "New York" date: 20220601-20230601'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == ""
    assert query.start_date == "20220601"
    assert query.end_date == "20230601"


def test_dates_with_missing_day():
    # Date missing the day, assuming end of month or beginning depending on context
    message = 'hiking "New York" date: 202204-20230602'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == ""
    assert query.start_date == "202204"  # Assuming default to the first of the month
    assert query.end_date == "20230602"  # Assuming default to the end of the month


def test_dates_with_missing_month_and_day():
    # Date missing both month and day
    message = 'hiking "New York" date: 2022-2023'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == ""
    assert query.start_date == "2022"  # Assuming default to the first of the year
    assert query.end_date == "2023"  # Assuming default to the end of the year


def test_mixed_order():
    message = 'hiking "New York" cap: Exploring Central Park date: 20220601-20230601'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == "Exploring Central Park"
    assert query.start_date == "20220601"
    assert query.end_date == "20230601"


def test_incorrect_date_order():
    message = 'hiking "New York" date: 20230601-20220601'
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == ""
    assert query.start_date == "20220601"
    assert query.end_date == "20230601"


# Test handling of non-standard quotes
def test_non_standard_quotes():
    message = "hiking “New York” cap: Exploring Central Park"
    query = parse_blocks(message)
    assert query.tags == ["hiking", "New York"]
    assert query.caption == "Exploring Central Park"


# Test when there's only a caption
def test_caption_only():
    message = "cap: A quiet moment"
    query = parse_blocks(message)
    assert query.tags == []
    assert query.caption == "A quiet moment"
    assert query.start_date is None
    assert query.end_date is None


# Test when there's only a date
def test_date_only():
    message = "date: 20220601-20230601"
    query = parse_blocks(message)
    assert query.tags == []
    assert query.caption == ""
    assert query.start_date == "20220601"
    assert query.end_date == "20230601"


# Test when there's only a caption and a date
def test_caption_and_date_only():
    message = "cap: A quiet moment date: 20220601-20230601"
    query = parse_blocks(message)
    assert query.tags == []
    assert query.caption == "A quiet moment"
    assert query.start_date == "20220601"
    assert query.end_date == "20230601"


# Test when there's only tags
def test_tag_only():
    message = "hiking climbing"
    query = parse_blocks(message)
    assert query.tags == ["hiking", "climbing"]
    assert query.caption == ""
    assert query.start_date is None
    assert query.end_date is None

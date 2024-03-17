import json
import os

from core import ACDReceive


def main():
    """Start the bot."""
    with open(os.path.join(os.path.dirname(__file__), "secrets.json"), "r") as f:
        secrets = json.load(f)
    telegram_token = secrets["telegram-token"]
    anyscale_token = secrets["anyscale"]

    metadata_path = "db.csv"
    storage_path = "imgs"

    bot = ACDReceive(
        metadata_path,
        storage_path,
        telegram_token=telegram_token,
        anyscale_token=anyscale_token,
    )
    bot.run()


if __name__ == "__main__":
    main()

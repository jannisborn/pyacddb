import json
import os

from acdreceive.core import ACDReceive


def main():
    """Start the bot."""
    with open(os.path.join(os.path.dirname(__file__), "secrets.json"), "r") as f:
        secrets = json.load(f)

    metadata_path = "wholedb.csv"
    storage_path = "imgs"
    storage_path = secrets["smartdrive-host"]

    bot = ACDReceive(metadata_path, storage_path, secrets=secrets)
    bot.run()


if __name__ == "__main__":
    main()

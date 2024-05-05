import os
import re
import time
from collections import defaultdict
from datetime import datetime
from random import random
from typing import Any, Dict, List

import pandas as pd
import telegram
from loguru import logger
from telegram import Message, Update
from telegram.ext import CommandHandler, Filters, MessageHandler, Updater

from .dataclient import Client
from .llm import INSTRUCTION_MESSAGE, LLM
from .metadata import IMAGE_FORMATS, VIDEO_FORMATS
from .utils import parse_tags


class ACDReceive:
    def __init__(self, db_path: str, storage_path: str, secrets: Dict[str, Any]):
        """
        Initialize the bot with the given tokens and paths.

        Args:
            db_path: Path to the metadata file
            storage_path: Path to the directory containing the images. This can be a
                local directory or a cloud storage bucket.
            secrets: A dictionary containing the Telegram and AnyScale tokens
        """
        # Load tokens and initialize variables
        self.telegram_token = secrets["telegram"]
        self.anyscale_token = secrets["anyscale"]

        # Initialize language preferences dictionary
        self.user_prefs = defaultdict(dict)

        # Initialize the bot and dispatcher
        self.updater = Updater(self.telegram_token, use_context=True)
        self.dp = self.updater.dispatcher

        # Register handlers
        self.dp.add_handler(
            CommandHandler(
                "start", lambda update, context: update.message.reply_text("Hi!")
            )
        )
        self.dp.add_handler(
            MessageHandler(Filters.text & (~Filters.command), self.handle_text_message)
        )
        self.db_setup(db_path)
        self.max_images = 10
        if (
            storage_path.startswith("gs://")
            or storage_path.startswith("s3://")
            or storage_path.startswith("http")
        ):
            self.storage = "cloud"
            self.get_medium = self.get_medium_cloud
            self.data_client = Client(
                host=storage_path,
                root=secrets["smartdrive-root"],
                username=secrets["smartdrive-login"],
                password=secrets["smartdrive-password"],
            )
        else:
            self.storage = "local"
            self.get_medium = self.get_medium_local

        self.data_path = storage_path

    def db_setup(self, db_path: str):
        db = pd.read_csv(db_path)
        db["FileType"] = db["FileType"].replace("Portable Network Graphics", "png")
        db["FileType"] = db["FileType"].str.lower()
        self.tags = list(db.columns)[list(db.columns).index("Tags") + 1 :]
        db.columns = db.columns.str.lower()
        db = db.rename(columns={"name": "Name"})  # to avoid conflict with build-in
        db = db[~db.filetype.isin(["ordner", "xmp files"])]

        if any(
            [x not in IMAGE_FORMATS and x not in VIDEO_FORMATS for x in db["filetype"]]
        ):
            raise ValueError(f"Unknown format in data: {db['filetype'].value_counts()}")
        self.db = db

    def setup(self, update, context) -> bool:
        """
        Set up the user's language preference and collect their name.
        Returns whether the user message was part of the setup process.
        """
        user_id = update.message.from_user.id
        # Check if the user's language preference is already set
        if user_id not in self.user_prefs:
            context.bot.send_chat_action(
                chat_id=update.message.chat_id, action=telegram.ChatAction.TYPING
            )
            update.message.reply_text("Willkommen!\nDas is Michaels ACDReceiver!📷")
            time.sleep(0.7)
            update.message.reply_text("Hier ist die Anleitung!")
            time.sleep(1)
            response_message = update.message.reply_text(
                INSTRUCTION_MESSAGE, parse_mode="Markdown"
            )
            try:
                context.bot.unpin_all_chat_messages(chat_id=update.message.chat_id)
            except Exception:
                logger.warning("Failed to unpin messages")
            context.bot.pin_chat_message(
                chat_id=update.message.chat_id,
                message_id=response_message.message_id,
                disable_notification=False,
            )
            self.user_prefs[user_id]["setup_complete"] = True
            return True
        return False

    def return_message(self, update: Update, text: str) -> Message:
        return update.message.reply_text(text)

    def handle_text_message(self, update, context):

        if random() < 0.005:
            output = self.joke_llm(update.message.text)
            self.return_message(update, output)
            return
        is_setting_up = self.setup(update, context)
        if is_setting_up:
            return

        user_id = update.message.from_user.id
        message = update.message.text.lower().strip()
        if self.user_prefs[user_id].get("collecting_displayall", False):
            if message in ["ja", "gerne", "yes", "y", "👍"]:
                self.display_results(update, context, self.user_prefs[user_id]["imgs"])
            else:
                self.return_message(
                    update,
                    "Kein Problem, versuch's gerne mit einer anderen Anfrage!",
                )
            self.user_prefs[user_id]["collecting_displayall"] = False
            self.user_prefs[user_id]["imgs"] = []
            return
        elif message == "tags":
            update.message.reply_text(
                f"Die aktuelle Datenbank hat {len(self.db)} Einträge und {len(self.tags)} tags"
            )
            time.sleep(0.6)
            self.send_tag_distribution(update)
            return

        self.search_tags_in_db(update, context)

    def send_tag_distribution(self, update):
        message_buffer = "Die verfügbaren Tags und ihre Verbreitung:\n\n"
        for tag in self.tags:
            tag_info = f"{tag}: {len(self.db[self.db[tag.lower().strip()]])}\n"

            # Check if adding this tag info will exceed the limit
            if len(message_buffer) + len(tag_info) > 1000:
                update.message.reply_text(message_buffer)
                message_buffer = ""  # Reset the buffer after sending

            message_buffer += tag_info

        # Send any remaining text in the buffer
        if message_buffer:
            update.message.reply_text(message_buffer)

    def search_tags_in_db(self, update, context):
        """Search for tags in the database when a message is received."""

        try:
            user_id = update.message.from_user.id
            # Parse the message
            message = update.message.text.lower()
            tags = parse_tags(message)
            logger.info(f"Searching for {tags}")
            query = (
                " ".join([t.capitalize() + " AND " for t in tags[:-1]])
                + tags[-1].capitalize()
            )

            result_df = self.lookup(update, tags)
            if len(result_df) == 0:
                self.return_message(update, f"Null Ergebnisse für Anfrage: {query}!")
                return
            elif len(result_df) == len(self.db):
                self.return_message(
                    update,
                    "Das hat nicht geklappt. Probier's nochmal mit einer anderen Anfrage!",
                )
            elif len(result_df) > self.max_images:
                self.return_message(
                    update,
                    f"{len(result_df)} Ergebnisse gefunden! Willst du sie alle sehen?",
                )

                self.user_prefs[user_id]["collecting_displayall"] = True
                self.user_prefs[user_id]["imgs"] = result_df
                return
            else:
                self.display_results(update, context, result_df)

        except Exception as e:
            response = f"An error occurred: {e}"
            self.return_message(update, response)

    def get_medium_local(self, path: str):
        """Reads a file from local storage and returns its content."""
        with open(os.path.join(self.data_path, path), "rb") as medium:
            return medium

    def get_medium_cloud(self, path: str):
        """Retrieves file content from cloud storage and returns it."""
        content = self.data_client.get_file_content(path)
        return content

    def display_results(self, update, context, result_df: pd.DataFrame):
        self.return_message(update, f"Here are the {len(result_df)} results!")
        # Send each image to the chat
        for i, row in result_df.iterrows():
            path = row.folder.split("Public\Fotos\\")[-1] + row.Name
            _, file_extension = os.path.splitext(path)
            file_extension = file_extension[1:].lower()
            text = ""
            if not row.empty:
                text += str(row["caption"])
                text += f" (von {row['author'].split(' ')[0]}"

                db_date_str = row["dbdate"]
                db_date = datetime.strptime(db_date_str, "%Y%m%d %H:%M:%S.%f")
                nice_date = db_date.strftime("%d.%m.%Y %H:%M")
                text += f" am {nice_date})"

            if file_extension in VIDEO_FORMATS:
                self.return_message(update, f"Video {path} not in storage")
                continue

            medium = self.get_medium(path)
            if medium is None:
                self.return_message(update, f"Failed to retrieve {path}")
                continue
            if file_extension in IMAGE_FORMATS:
                context.bot.send_photo(
                    chat_id=update.message.chat_id, photo=medium, caption=text
                )
            # elif file_extension in VIDEO_FORMATS:
            #     self.return_message(
            #         update, f"Video {file_extension}"
            #     )
            #     context.bot.send_video(chat_id=update.message.chat_id, video=medium)
            else:
                self.return_message(
                    update, f"Unsupported file format: {file_extension}"
                )

    def lookup(self, update, tags: List[str]) -> pd.DataFrame:
        # TODO: Lookup with caption like this:
        # Micha Agnes Cosy Caption: schön
        df = self.db

        for tag in tags:
            if tag not in df.columns:
                self.return_message(
                    update,
                    f"Tag {tag.capitalize()} nicht in der Datenbank vorhanden! Wird ignoriert.",
                )
                continue
            df = df[df[tag.lower()]]
            self.return_message(
                update,
                f"Tag {tag.capitalize()} gefunden, jetzt noch {len(df)} Einträge.",
            )

        return df

    def run(self):
        logger.info("Starting bot")
        self.updater.start_polling()
        self.updater.idle()

    def set_llms(self):
        self.joke_llm = LLM(
            model="Open-Orca/Mistral-7B-OpenOrca",
            token=self.anyscale_token,
            task_prompt=("Erzähl mir einen kurzen Witz zum Thema Fotografieren"),
            temperature=0.6,
        )

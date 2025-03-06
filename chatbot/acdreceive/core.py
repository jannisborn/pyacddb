import os
import time
from collections import defaultdict
from datetime import datetime
from random import random
from typing import Any, Dict

import pandas as pd
import telegram
from loguru import logger
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    Filters,
    MessageHandler,
    Updater,
)

from .dataclient import Client
from .llm import INSTRUCTION_MESSAGE, LLM
from .metadata import IMAGE_FORMATS, VIDEO_FORMATS
from .utils import Query, parse_blocks


class ACDReceive:

    PAGESIZE = 10

    def __init__(self, db_path: str, storage_path: str, secrets: Dict[str, Any]):
        """
        Initialize the bot with the given tokens and paths.

        Args:
            db_path: Path to the metadata file
            storage_path: Path to the directory containing the images. This can be a
                local directory or a cloud storage bucket.
            secrets: A dictionary containing the Telegram and LLM API tokens
        """
        # Load tokens and initialize variables
        self.telegram_token = secrets["telegram"]
        self.llm_token = secrets["together"]

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
        self.dp.add_handler(CallbackQueryHandler(self.callback_query_handler))

        self.db_setup(db_path)
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
        self.joke_llm = LLM(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            token=self.llm_token,
            task_prompt=("Erzähl mir einen kurzen Witz zum Thema Fotografieren"),
            temperature=0.6,
        )

    def db_setup(self, db_path: str):
        db = pd.read_csv(db_path)
        db["FileType"] = db["FileType"].replace("Portable Network Graphics", "png")
        db["FileType"] = db["FileType"].str.lower()
        self.tags = sorted(list(db.columns)[list(db.columns).index("Tags") + 1 :])
        db.columns = db.columns.str.lower()
        db = db.rename(columns={"name": "Name"})  # to avoid conflict with build-in
        db = db[~db.filetype.isin(["ordner", "xmp files"])]
        db["caption"] = db["caption"].fillna("")
        db["year"] = pd.to_datetime(db["dbdate"]).dt.year
        db["month"] = pd.to_datetime(db["dbdate"]).dt.month
        db["day"] = pd.to_datetime(db["dbdate"]).dt.day

        if any(
            [x not in IMAGE_FORMATS and x not in VIDEO_FORMATS for x in db["filetype"]]
        ):
            raise ValueError(f"Unknown format in data: {db['filetype'].value_counts()}")
        self.db = db

    def setup(self, update, context, force: bool=False) -> bool:
        """
        Set up the user's language preference and collect their name.
        Returns whether the user message was part of the setup process.
        """
        user_id = update.message.from_user.id
        # Check if the user's language preference is already set
        if force or user_id not in self.user_prefs:
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

        message = update.message.text.lower().strip()
        
        force = message.startswith('help')
        is_setting_up = self.setup(update, context, force=force)
        if is_setting_up:
            return

        if random() < 0.01:
            output = self.joke_llm(update.message.text)
            self.return_message(update, output)
            return
        
        if message == "tags":
            update.message.reply_text(
                f"Die aktuelle Datenbank hat {len(self.db)} Einträge und {len(self.tags)} tags"
            )
            time.sleep(0.6)
            self.send_tag_distribution(update)
            return

        self.search_tags_in_db(update, context)

    def send_tag_distribution(self, update):
        message_buffer = "Die verfügbaren Tags und ihre Verbreitung:\n\n"
        for tag in sorted(self.tags):
            tag_info = f"{tag}: {len(self.db[self.db[tag.lower().strip()]])}\n"

            # Check if adding this tag info will exceed the limit
            if len(message_buffer) + len(tag_info) > 1000:
                update.message.reply_text(message_buffer)
                message_buffer = ""  # Reset the buffer after sending

            message_buffer += tag_info

        # Send any remaining text in the buffer
        if message_buffer:
            update.message.reply_text(message_buffer)

    def query_date(
        self, df: pd.DataFrame, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """
        Queries a DataFrame for records within a specified date range.

        The date range is provided as a string in the format 'YYYYMMDD-YYYYMMDD',
        where both month and day are optional. If the month or day is omitted,
        it defaults to the start of the period for the start date (i.e., January 1st)
        and the end of the period for the end date (i.e., December 31st).

        Parameters:
            df (pd.DataFrame): A DataFrame with separate columns 'Year', 'Month', and 'Day'.
            start_date (str): A string specifying the starting date, formatted as 'YYYYMMDD'
            end_date (str): A string specifying the end date, formatted as 'YYYYMMDD'.

        Returns:
            pd.DataFrame: A DataFrame containing the rows that fall within the specified date range.
        """
        # Extract the start and end dates from the date_range string
        start_year = int(start_date[:4])
        start_month = int(start_date[4:6]) if len(start_date) > 4 else 1
        start_day = int(start_date[6:]) if len(start_date) > 6 else 1
        end_year = int(end_date[:4])
        end_month = int(end_date[4:6]) if len(end_date) > 4 else 12
        end_day = int(end_date[6:]) if len(end_date) > 6 else 31
        # Create a boolean mask to filter DataFrame rows within the date range
        mask = (
            (df["year"] >= start_year)
            & (df["month"] >= start_month)
            & (df["day"] >= start_day)
        ) & (
            (df["year"] <= end_year)
            & (df["month"] <= end_month)
            & (df["day"] <= end_day)
        )

        return df[mask]

    def search_tags_in_db(self, update, context):
        """Search for tags in the database when a message is received."""

        try:
            user_id = update.message.from_user.id
            # Parse the message
            message = update.message.text.lower()
            query = parse_blocks(message)
            tags = query.tags
            caption = query.caption
            start = query.start_date
            end = query.end_date
            logger.info(
                f"Searching for {tags} with caption {caption} and date {start} - {end}"
            )
            userquery = (
                " ".join([t.capitalize() + " AND " for t in tags[:-1]])
                + (tags[-1].capitalize() if len(tags) > 0 else "")
                + (f"; Caption: {caption}" if caption != "" else "")
                + (f"; Date: {start} - {end}" if start is not None else "")
            )

            result_df = self.lookup(update, query)
            result_df = result_df.sample(frac=1)
            if len(result_df) == 0:
                self.return_message(update, f"Null Ergebnisse für Anfrage: {userquery}")
                return
            elif len(result_df) == len(self.db):
                self.return_message(
                    update,
                    "Das hat nicht geklappt. Probier's nochmal mit einer anderen Anfrage!",
                )
            else:
                self.user_prefs[user_id]["current_result"] = result_df
                l = len(result_df)
                if l > self.PAGESIZE:
                    msg = f"{l} Ergebnisse, hier sind die ersten {self.PAGESIZE}"
                else:
                    msg = f"Hier sind die {l} Ergebnisse"
                self.return_message(update, msg)
                self.keep_displaying_results(update, context, user_id)

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

    def keep_displaying_results(
        self, update, context, user_id: int, start_index: int = 0
    ):

        result_df = self.user_prefs[user_id]["current_result"]
        end_index = start_index + self.PAGESIZE
        current_page = result_df.iloc[start_index:end_index]

        # Send each image to the chat
        for i, row in current_page.iterrows():
            # logger.debug(f"FOlder {row.folder} and {type(row.folder)}")
            path = row.folder.split("Public\Fotos\\")[-1] + row.Name
            _, file_extension = os.path.splitext(path)
            file_extension = file_extension[1:].lower()
            text = ""
            if not row.empty:
                text += str(row["caption"])
                text += (
                    f" (von {row['author'].split(' ')[0]} "
                    if isinstance(row.author, str)
                    else " ("
                )

                db_date_str = row["dbdate"]
                db_date = datetime.strptime(db_date_str, "%Y%m%d %H:%M:%S.%f")
                nice_date = db_date.strftime("%d.%m.%Y %H:%M")
                text += f"am {nice_date})"

            medium = self.get_medium(path)
            if medium is None:
                self.return_message(update, f"Failed to retrieve {path}")
                continue
            if file_extension in IMAGE_FORMATS:
                context.bot.send_photo(
                    chat_id=update.message.chat_id, photo=medium, caption=text
                )
            elif file_extension in VIDEO_FORMATS:
                self.return_message(update, f"Video {file_extension}")
                context.bot.send_video(chat_id=update.message.chat_id, video=medium)
            else:
                self.return_message(
                    update, f"Unsupported file format: {file_extension}"
                )

        # Add a button for pagination if there are more results to show
        if len(result_df) > end_index:
            keyboard = [
                [
                    InlineKeyboardButton(
                        "Klicke für mehr!", callback_data=f"see_more_{end_index}"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(
                "Willst du mehr sehen?", reply_markup=reply_markup
            )
        else:
            update.message.reply_text("Das war alles 🙂")

    def lookup(self, update, query: Query) -> pd.DataFrame:
        df = self.db

        for tag in query.tags:
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
        # Now check for caption and date
        if query.caption != "":
            df = df[df.caption.str.lower().str.contains(query.caption.lower())]
        if query.start_date is not None and query.end_date is not None:
            df = self.query_date(df, query.start_date, query.end_date)

        return df

    def callback_query_handler(self, update, context):
        """
        Handles callback queries for pagination of special coins display.
        """
        query = update.callback_query
        query.answer()
        user_id = query.from_user.id
        data = query.data

        if data.startswith("see_more_"):
            start_index = int(data.split("_")[-1])
            logger.debug(
                f"Continue displaying from entry {start_index} for user {user_id}"
            )
            self.keep_displaying_results(query, context, user_id, start_index)

    def run(self):
        logger.info("Starting bot")
        self.updater.start_polling()
        self.updater.idle()

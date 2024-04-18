import os

import requests
from loguru import logger
from requests.auth import HTTPBasicAuth


class Client:
    def __init__(self, host: str, root: str, username: str, password: str):
        self.host = host
        self.root = root
        self.username = username
        self.password = password

        self.data_root = os.path.join(self.host, self.root)

    def get_file_content(self, remote_path: str):
        """Downloads file content directly into memory."""
        url = os.path.join(self.data_root, remote_path)
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))

        if response.status_code == 200:
            logger.debug(f'Loaded file {url}')
            return response.content
        else:
            logger.error(
                f"Failed to retrieve file {remote_path}: {response.status_code}"
            )
            return None

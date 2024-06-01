import io
import os

import requests
from loguru import logger
from PIL import Image
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
        remote_path = remote_path.replace("\\", "/")
        url = os.path.join(self.data_root, remote_path)
        response = requests.get(url, auth=HTTPBasicAuth(self.username, self.password))

        if response.status_code == 200:
            content = response.content
            size = len(content) / (1024**2)
            logger.debug(f"Retrieved file {remote_path} of size {size:.3f} MB")
            if size > 5:
                logger.info(
                    f"Image {remote_path} is larger than 5MB ({size:.3f}), downscaling..."
                )
                content = self.downscale_image(response.content)
                size_bytes = len(content)
                size_mb = size_bytes / (1024 * 1024)
                logger.info(f"Downscaled image size: {size_mb:.2f} MB")

            return content
        else:
            logger.error(
                f"Failed to retrieve file {remote_path}: {response.status_code}"
            )
            return None

    def downscale_image(self, image_content):
        """Downscale the image to approximately 4MB."""
        image = Image.open(io.BytesIO(image_content))

        # Convert image to RGB if it is not already in that mode
        if image.mode != "RGB":
            image = image.convert("RGB")

        quality = 85
        while True:
            buffer = io.BytesIO()
            image.save(buffer, format="JPEG", quality=quality)
            size_bytes = buffer.tell()
            size_mb = size_bytes / (1024 * 1024)

            if size_mb <= 4 or quality <= 20:
                break

            quality -= 5

        return buffer.getvalue()

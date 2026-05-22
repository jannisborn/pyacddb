from pyacddb.acdreceive.dataclient import Client


class FakeResponse:
    def __init__(self, content: bytes, status_code: int = 200):
        self.content = content
        self.status_code = status_code


def test_large_video_is_not_downscaled(monkeypatch):
    content = b"0" * (6 * 1024 * 1024)
    client = Client("https://example.com", "root", "user", "password")

    monkeypatch.setattr(
        "pyacddb.acdreceive.dataclient.requests.get",
        lambda url, auth: FakeResponse(content),
    )

    def fail_downscale(image_content):
        raise AssertionError("videos must not be sent through PIL downscaling")

    monkeypatch.setattr(client, "downscale_image", fail_downscale)

    assert client.get_file_content("folder/video.mp4") == content


def test_large_image_is_downscaled(monkeypatch):
    content = b"0" * (6 * 1024 * 1024)
    downscaled = b"small"
    client = Client("https://example.com", "root", "user", "password")

    monkeypatch.setattr(
        "pyacddb.acdreceive.dataclient.requests.get",
        lambda url, auth: FakeResponse(content),
    )
    monkeypatch.setattr(client, "downscale_image", lambda image_content: downscaled)

    assert client.get_file_content("folder/image.jpg") == downscaled

from pyacddb.acdreceive.core import (
    TELEGRAM_UPLOAD_LIMIT_BYTES,
    media_exceeds_telegram_upload_limit,
)


def test_media_at_telegram_upload_limit_is_allowed():
    assert not media_exceeds_telegram_upload_limit(b"0" * TELEGRAM_UPLOAD_LIMIT_BYTES)


def test_media_above_telegram_upload_limit_is_rejected():
    assert media_exceeds_telegram_upload_limit(b"0" * (TELEGRAM_UPLOAD_LIMIT_BYTES + 1))

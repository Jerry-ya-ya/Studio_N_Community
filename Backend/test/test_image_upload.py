from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin
from werkzeug.datastructures import FileStorage

from image_upload import (
    InvalidImageError,
    delete_uploaded_image,
    encode_validated_image,
    upload_validated_image,
)


def build_png_with_metadata():
    output = BytesIO()
    metadata = PngImagePlugin.PngInfo()
    metadata.add_text("Comment", "untrusted metadata")
    Image.new("RGB", (8, 8), (20, 80, 140)).save(
        output,
        format="PNG",
        pnginfo=metadata,
    )
    output.seek(0)
    return output


def test_valid_image_is_detected_and_reencoded_without_trusting_extension():
    uploaded_file = FileStorage(
        stream=build_png_with_metadata(),
        filename="avatar.php",
        content_type="application/x-php",
    )

    payload, extension, content_type = encode_validated_image(uploaded_file)

    assert extension == "png"
    assert content_type == "image/png"
    with Image.open(payload) as saved_image:
        assert saved_image.format == "PNG"
        assert saved_image.size == (8, 8)
        assert "Comment" not in saved_image.info


def test_fake_image_with_allowed_extension_is_rejected():
    uploaded_file = FileStorage(
        stream=BytesIO(b"<script>alert('not an image')</script>"),
        filename="attack.png",
        content_type="image/png",
    )

    with pytest.raises(InvalidImageError, match="有效的圖片"):
        encode_validated_image(uploaded_file)


class FakeBlobClient:
    def __init__(self, name):
        self.name = name
        self.url = f"https://example.blob.core.windows.net/media/{name}"
        self.uploads = []

    def upload_blob(self, payload, **kwargs):
        self.uploads.append((payload, kwargs))


class FakeContainerClient:
    url = "https://example.blob.core.windows.net/media"

    def __init__(self):
        self.blobs = {}
        self.deleted = []

    def get_blob_client(self, name):
        return self.blobs.setdefault(name, FakeBlobClient(name))

    def delete_blob(self, name, **kwargs):
        self.deleted.append((name, kwargs))


class FakeBlobServiceClient:
    def __init__(self, container):
        self.container = container

    def get_container_client(self, name):
        assert name == "media"
        return self.container


def test_uploads_sanitized_images_to_azure_and_deletes_its_own_blobs(app):
    container = FakeContainerClient()
    app.config.update(
        AZURE_BLOB_SERVICE_CLIENT=FakeBlobServiceClient(container),
        AZURE_STORAGE_CONTAINER="media",
    )
    uploaded_file = FileStorage(
        stream=build_png_with_metadata(),
        filename="avatar.png",
        content_type="image/png",
    )

    with app.app_context():
        stored_image = upload_validated_image(uploaded_file, "avatars/user-1")
        assert stored_image.blob_name.startswith("avatars/user-1/")
        assert stored_image.url.endswith(stored_image.blob_name)

        blob = container.blobs[stored_image.blob_name]
        payload, options = blob.uploads[0]
        assert payload
        assert options["content_settings"].content_type == "image/png"
        assert options["cache_control"] == "public, max-age=31536000, immutable"

        assert delete_uploaded_image(stored_image.url) is True

    assert container.deleted == [
        (stored_image.blob_name, {"delete_snapshots": "include"})
    ]

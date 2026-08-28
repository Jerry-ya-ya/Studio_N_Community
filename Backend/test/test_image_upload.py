from io import BytesIO

import pytest
from PIL import Image, PngImagePlugin
from werkzeug.datastructures import FileStorage

from image_upload import InvalidImageError, save_validated_image


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


def test_valid_image_is_detected_and_reencoded_without_trusting_extension(tmp_path):
    uploaded_file = FileStorage(
        stream=build_png_with_metadata(),
        filename="avatar.php",
        content_type="application/x-php",
    )

    filename = save_validated_image(uploaded_file, str(tmp_path), "user-1")

    assert filename.startswith("user-1_")
    assert filename.endswith(".png")
    with Image.open(tmp_path / filename) as saved_image:
        assert saved_image.format == "PNG"
        assert saved_image.size == (8, 8)
        assert "Comment" not in saved_image.info


def test_fake_image_with_allowed_extension_is_rejected(tmp_path):
    uploaded_file = FileStorage(
        stream=BytesIO(b"<script>alert('not an image')</script>"),
        filename="attack.png",
        content_type="image/png",
    )

    with pytest.raises(InvalidImageError, match="有效的圖片"):
        save_validated_image(uploaded_file, str(tmp_path), "user-1")

    assert list(tmp_path.iterdir()) == []

import uuid
import warnings
from dataclasses import dataclass
from io import BytesIO
from urllib.parse import unquote, urlparse

from azure.core.exceptions import AzureError
from azure.storage.blob import BlobServiceClient, ContentSettings
from flask import current_app
from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError


Image.MAX_IMAGE_PIXELS = 25_000_000

ALLOWED_IMAGE_FORMATS = {
    "GIF": ("gif", "GIF", "image/gif"),
    "JPEG": ("jpg", "JPEG", "image/jpeg"),
    "PNG": ("png", "PNG", "image/png"),
    "WEBP": ("webp", "WEBP", "image/webp"),
}
MAX_IMAGE_WIDTH = 8_192
MAX_IMAGE_HEIGHT = 8_192
MAX_ANIMATION_FRAMES = 100
MAX_TOTAL_ANIMATION_PIXELS = 50_000_000


class InvalidImageError(ValueError):
    pass


class ImageStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredImage:
    blob_name: str
    url: str


def _validate_dimensions(image):
    width, height = image.size
    if width <= 0 or height <= 0:
        raise InvalidImageError("圖片尺寸無效")
    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise InvalidImageError("圖片尺寸過大")


def _load_verified_image(uploaded_file):
    try:
        uploaded_file.stream.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(uploaded_file.stream) as probe:
                detected_format = probe.format
                if detected_format not in ALLOWED_IMAGE_FORMATS:
                    raise InvalidImageError("只接受 PNG、JPEG、GIF 或 WebP 圖片")
                _validate_dimensions(probe)
                probe.verify()

        uploaded_file.stream.seek(0)
        image = Image.open(uploaded_file.stream)
        _validate_dimensions(image)
        return image, detected_format
    except InvalidImageError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise InvalidImageError("圖片像素數過大")
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise InvalidImageError("檔案不是有效的圖片")


def _save_static_image(image, detected_format, destination):
    normalized = ImageOps.exif_transpose(image)
    save_options = {}

    if detected_format == "JPEG":
        normalized = normalized.convert("RGB")
        save_options = {"quality": 90, "optimize": True}
    elif detected_format == "PNG":
        normalized = normalized.convert("RGBA" if "A" in normalized.getbands() else "RGB")
        save_options = {"optimize": True}
    elif detected_format == "WEBP":
        normalized = normalized.convert("RGBA" if "A" in normalized.getbands() else "RGB")
        save_options = {"quality": 90, "method": 6}
    else:
        normalized = normalized.convert("P", palette=Image.Palette.ADAPTIVE)

    normalized.save(destination, format=ALLOWED_IMAGE_FORMATS[detected_format][1], **save_options)


def _save_animated_gif(image, destination):
    frame_count = getattr(image, "n_frames", 1)
    if frame_count > MAX_ANIMATION_FRAMES:
        raise InvalidImageError("GIF 動畫幀數過多")

    frames = []
    durations = []
    total_pixels = 0

    for frame in ImageSequence.Iterator(image):
        _validate_dimensions(frame)
        total_pixels += frame.width * frame.height
        if total_pixels > MAX_TOTAL_ANIMATION_PIXELS:
            raise InvalidImageError("GIF 動畫總像素數過大")
        frames.append(frame.convert("RGBA"))
        durations.append(min(max(int(frame.info.get("duration", 100)), 20), 10_000))

    frames[0].save(
        destination,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=int(image.info.get("loop", 0)),
        disposal=2,
        optimize=True,
    )


def encode_validated_image(uploaded_file):
    """Validate, sanitize, and return an image payload ready for blob storage."""
    image, detected_format = _load_verified_image(uploaded_file)
    output = BytesIO()
    try:
        if detected_format == "GIF" and getattr(image, "is_animated", False):
            _save_animated_gif(image, output)
        else:
            _save_static_image(image, detected_format, output)
    except InvalidImageError:
        raise
    except (OSError, ValueError) as error:
        raise InvalidImageError("圖片無法安全地重新編碼") from error
    finally:
        image.close()

    output.seek(0)
    extension, _format, content_type = ALLOWED_IMAGE_FORMATS[detected_format]
    return output, extension, content_type


def _container_client():
    configured_client = current_app.config.get("AZURE_BLOB_SERVICE_CLIENT")
    container_name = current_app.config.get("AZURE_STORAGE_CONTAINER")
    connection_string = current_app.config.get("AZURE_STORAGE_CONNECTION_STRING")

    if not container_name or not (configured_client or connection_string):
        raise ImageStorageError(
            "Azure Blob Storage is not configured. Set "
            "AZURE_STORAGE_CONNECTION_STRING and AZURE_STORAGE_CONTAINER."
        )

    try:
        service_client = configured_client or BlobServiceClient.from_connection_string(connection_string)
        return service_client.get_container_client(container_name)
    except (AzureError, ValueError) as error:
        raise ImageStorageError("Unable to initialize Azure Blob Storage") from error


def upload_validated_image(uploaded_file, blob_prefix):
    """Store a sanitized image in Azure Blob Storage and return its public URL."""
    payload, extension, content_type = encode_validated_image(uploaded_file)
    blob_name = f"{blob_prefix.strip('/')}/{uuid.uuid4().hex}.{extension}"

    try:
        blob_client = _container_client().get_blob_client(blob_name)
        blob_client.upload_blob(
            payload.getvalue(),
            overwrite=False,
            content_settings=ContentSettings(content_type=content_type),
            cache_control="public, max-age=31536000, immutable",
        )
    except ImageStorageError:
        raise
    except AzureError as error:
        raise ImageStorageError("Unable to upload image to Azure Blob Storage") from error

    return StoredImage(blob_name=blob_name, url=blob_client.url)


def delete_uploaded_image(image_url):
    """Delete a URL only when it belongs to this application's blob container."""
    if not image_url or not isinstance(image_url, str):
        return False

    try:
        container_client = _container_client()
    except ImageStorageError:
        return False

    container_url = container_client.url.rstrip("/")
    if not image_url.startswith(f"{container_url}/"):
        return False

    blob_name = unquote(urlparse(image_url).path).lstrip("/")
    container_path = urlparse(container_url).path.strip("/")
    if not blob_name.startswith(f"{container_path}/"):
        return False

    blob_name = blob_name[len(container_path) + 1:]
    try:
        container_client.delete_blob(blob_name, delete_snapshots="include")
        return True
    except AzureError:
        current_app.logger.warning("Unable to delete Azure Blob image: %s", image_url)
        return False

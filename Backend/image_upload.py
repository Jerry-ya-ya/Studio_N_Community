import os
import tempfile
import uuid
import warnings

from PIL import Image, ImageOps, ImageSequence, UnidentifiedImageError


Image.MAX_IMAGE_PIXELS = 25_000_000

ALLOWED_IMAGE_FORMATS = {
    "GIF": ("gif", "GIF"),
    "JPEG": ("jpg", "JPEG"),
    "PNG": ("png", "PNG"),
    "WEBP": ("webp", "WEBP"),
}
MAX_IMAGE_WIDTH = 8_192
MAX_IMAGE_HEIGHT = 8_192
MAX_ANIMATION_FRAMES = 100
MAX_TOTAL_ANIMATION_PIXELS = 50_000_000


class InvalidImageError(ValueError):
    pass


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


def save_validated_image(uploaded_file, upload_folder, filename_prefix):
    image, detected_format = _load_verified_image(uploaded_file)
    extension = ALLOWED_IMAGE_FORMATS[detected_format][0]
    filename = f"{filename_prefix}_{uuid.uuid4().hex}.{extension}"
    os.makedirs(upload_folder, exist_ok=True)

    temporary = tempfile.NamedTemporaryFile(
        dir=upload_folder,
        prefix=".upload-",
        suffix=f".{extension}",
        delete=False,
    )
    temporary_path = temporary.name
    temporary.close()
    final_path = os.path.join(upload_folder, filename)

    try:
        if detected_format == "GIF" and getattr(image, "is_animated", False):
            _save_animated_gif(image, temporary_path)
        else:
            _save_static_image(image, detected_format, temporary_path)
        os.replace(temporary_path, final_path)
    except InvalidImageError:
        raise
    except (OSError, ValueError) as error:
        raise InvalidImageError("圖片無法安全地重新編碼") from error
    finally:
        image.close()
        if os.path.exists(temporary_path):
            os.remove(temporary_path)

    return filename

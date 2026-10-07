import logging
import os
from io import BytesIO
from celery import shared_task
from django.conf import settings
from django.db.models import F as models_F

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    name="vehicles.tasks.process_vehicle_image",
)
def process_vehicle_image(self, image_id: int):
    """
    Background image processing after upload:
    - Validate image is safe
    - Re-encode (strip EXIF, normalize format)
    - Generate thumbnail
    - Generate WebP variant
    - Record dimensions and file size
    Never called synchronously in a request.
    """
    try:
        from PIL import Image as PILImage
        from vehicles.models import VehicleImage

        img_obj = VehicleImage.objects.select_related(
            "vehicle").get(pk=image_id)

        with PILImage.open(img_obj.image.path) as pil_img:
            # Strip EXIF, normalize orientation
            pil_img = _normalize_image(pil_img)

            # Record dimensions
            img_obj.width = pil_img.width
            img_obj.height = pil_img.height
            img_obj.file_size = img_obj.image.size

            # Generate thumbnail (400×280, cover crop)
            thumb_size = settings.THUMBNAIL_SIZES["card"]
            thumb = _resize_cover(pil_img.copy(), thumb_size)
            thumb_buffer = BytesIO()
            thumb.save(thumb_buffer, format="JPEG", quality=85, optimize=True)
            thumb_buffer.seek(0)

            from django.core.files.base import ContentFile
            thumb_name = f"thumb_{os.path.basename(img_obj.image.name)}"
            # Strip extension and force .jpg
            thumb_name = os.path.splitext(thumb_name)[0] + ".jpg"
            img_obj.thumbnail.save(thumb_name, ContentFile(
                thumb_buffer.read()), save=False)

            img_obj.save(update_fields=["thumbnail",
                         "width", "height", "file_size"])

        logger.info("Image %d processed successfully.", image_id)

    except Exception as exc:
        logger.error("Image processing failed for image %d: %s", image_id, exc)
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


@shared_task(name="vehicles.tasks.update_view_counts")
def update_view_counts(vehicle_id: int, increment: int = 1):
    """
    Batch-update view counts from Redis tallies.
    Called periodically by Celery Beat rather than on every request.
    """
    try:
        from vehicles.models import Vehicle
        Vehicle.objects.filter(pk=vehicle_id).update(
            view_count=models_F("view_count") + increment
        )
    except Exception as e:
        logger.error(
            "View count update failed for vehicle %d: %s", vehicle_id, e)


@shared_task(name="vehicles.tasks.warm_vehicle_caches")
def warm_vehicle_caches():
    """
    Pre-warm frequently accessed caches after bulk updates.
    Called by Celery Beat every 10 minutes.
    """
    try:
        from vehicles.models import Vehicle, Make, Category
        from vehicles.cache import (
            KEY_HOMEPAGE_FEATURED, KEY_HOMEPAGE_ARRIVALS,
            KEY_ALL_MAKES, KEY_POPULAR_MAKES,
            KEY_ALL_CATEGORIES, KEY_POPULAR_CATEGORIES,
            TIMEOUT_MEDIUM, TIMEOUT_LONG,
        )
        from django.core.cache import cache

        # Featured vehicles
        featured = list(
            Vehicle.objects.filter(
                is_published=True, featured=True, status="AVAILABLE")
            .select_related("make", "model", "category")
            .prefetch_related("images")
            .order_by("-published_at")[:8]
            .values(
                "id", "slug", "year", "make__name", "model__name",
                "variant", "price", "pricing_type", "condition",
                "mileage", "fuel_type", "transmission",
            )
        )
        cache.set(KEY_HOMEPAGE_FEATURED, featured, timeout=TIMEOUT_MEDIUM)

        # Popular makes
        makes = list(
            Make.objects.filter(is_popular=True)
            .order_by("sort_order", "name")
            .values("id", "name", "slug")
        )
        cache.set(KEY_POPULAR_MAKES, makes, timeout=TIMEOUT_LONG)

        # Popular categories
        categories = list(
            Category.objects.filter(is_popular=True)
            .order_by("sort_order", "name")
            .values("id", "name", "slug", "icon")
        )
        cache.set(KEY_POPULAR_CATEGORIES, categories, timeout=TIMEOUT_LONG)

        logger.info("Vehicle caches warmed.")
    except Exception as e:
        logger.error("Cache warming failed: %s", e)


# ── PIL helpers ───────────────────────────────────────────────────────────────

def _normalize_image(pil_img):
    """Strip EXIF orientation and convert to RGB."""
    from PIL import ImageOps
    try:
        pil_img = ImageOps.exif_transpose(pil_img)
    except Exception:
        pass
    if pil_img.mode not in ("RGB", "RGBA"):
        pil_img = pil_img.convert("RGB")
    elif pil_img.mode == "RGBA":
        background = __import__("PIL.Image", fromlist=["Image"]).Image.new(
            "RGB", pil_img.size, (255, 255, 255))
        background.paste(pil_img, mask=pil_img.split()[3])
        pil_img = background
    return pil_img


def _resize_cover(pil_img, size: tuple[int, int]):
    """Resize image to fill exact dimensions (cover crop)."""
    from PIL import Image as PILImage
    target_w, target_h = size
    src_w, src_h = pil_img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        new_h = target_h
        new_w = int(src_w * target_h / src_h)
    else:
        new_w = target_w
        new_h = int(src_h * target_w / src_w)

    pil_img = pil_img.resize((new_w, new_h), PILImage.LANCZOS)
    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    return pil_img.crop((left, top, left + target_w, top + target_h))

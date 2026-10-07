import logging
from django.db.models.signals import pre_save, post_save, post_delete
from django.dispatch import receiver
from .models import (
    Vehicle, PriceHistory, AuditLog,
    VehicleDocumentation, VehicleVerification,
    Make, Category,
)

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Vehicle)
def track_price_change(sender, instance, **kwargs):
    """Record price history before saving."""
    if not instance.pk:
        return
    try:
        old = Vehicle.objects.only("price").get(pk=instance.pk)
        if old.price != instance.price:
            PriceHistory.objects.create(
                vehicle=instance,
                old_price=old.price,
                new_price=instance.price,
                note="Admin price update",
            )
            if not instance.previous_price and old.price:
                instance.previous_price = old.price
    except Vehicle.DoesNotExist:
        pass


@receiver(post_save, sender=Vehicle)
def create_related_records(sender, instance, created, **kwargs):
    """Ensure every vehicle has documentation and verification records."""
    if created:
        VehicleDocumentation.objects.get_or_create(vehicle=instance)
        VehicleVerification.objects.get_or_create(vehicle=instance)
        AuditLog.objects.create(
            vehicle=instance,
            action=AuditLog.Action.CREATED,
            detail=f"Vehicle {instance.stock_number or instance.pk} created.",
        )
    _invalidate_caches(instance)


@receiver(post_delete, sender=Vehicle)
def invalidate_on_delete(sender, instance, **kwargs):
    _invalidate_caches(instance)


@receiver(post_save, sender=Make)
@receiver(post_delete, sender=Make)
def invalidate_makes_cache(sender, instance, **kwargs):
    from .cache import invalidate_makes_categories
    invalidate_makes_categories()


@receiver(post_save, sender=Category)
@receiver(post_delete, sender=Category)
def invalidate_categories_cache(sender, instance, **kwargs):
    from .cache import invalidate_makes_categories
    invalidate_makes_categories()


def _invalidate_caches(vehicle: Vehicle):
    try:
        from .cache import invalidate_vehicle
        invalidate_vehicle(
            vehicle_slug=getattr(vehicle, "slug", None),
            vehicle_id=vehicle.pk,
        )
    except Exception as e:
        logger.warning("Signal cache invalidation failed: %s", e)

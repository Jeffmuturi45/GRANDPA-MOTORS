import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(name="catalogue.tasks.warm_homepage_cache")
def warm_homepage_cache():
    """Warm all homepage section caches. Runs every 10 minutes."""
    from vehicles.tasks import warm_vehicle_caches
    warm_vehicle_caches.delay()
    logger.info("Homepage cache warm triggered.")

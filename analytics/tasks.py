import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    name="analytics.tasks.track_page_view",
    ignore_result=True,
    queue="analytics",
)
def track_page_view(
    path: str,
    method: str,
    status_code: int,
    user_agent: str,
    referer: str,
    ip_hash: str,
    session_key: str,
):
    """
    Async page view tracking — never blocks user requests.
    Full implementation in Phase 8.
    """
    # TODO Phase 8: write to analytics models
    pass


@shared_task(name="analytics.tasks.aggregate_daily_stats")
def aggregate_daily_stats():
    """Pre-aggregate analytics for the admin dashboard. Phase 8."""
    pass

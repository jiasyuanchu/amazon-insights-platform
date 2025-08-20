from celery import Celery
from celery.schedules import crontab
from src.app.core.config import settings

# Create Celery app
celery_app = Celery(
    "amazon_insights",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_RESULT_BACKEND),
    include=[
        "src.app.tasks.product_tasks",
        "src.app.tasks.scraping_tasks",
        "src.app.tasks.analysis_tasks",
        "src.app.tasks.competitor_tasks",
    ]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
)

# Configure periodic tasks
celery_app.conf.beat_schedule = {
    "daily-product-scraping": {
        "task": "src.app.tasks.scraping_tasks.scrape_all_products",
        "schedule": crontab(hour=2, minute=0),  # Run at 2 AM UTC daily
        "options": {"queue": "scraping"},
    },
    "hourly-price-monitoring": {
        "task": "monitor_price_changes",
        "schedule": crontab(minute=0),  # Run every hour
        "options": {"queue": "monitoring"},
    },
    "daily-competitive-analysis": {
        "task": "src.app.tasks.analysis_tasks.run_competitive_analysis",
        "schedule": crontab(hour=3, minute=0),  # Run at 3 AM UTC daily
        "options": {"queue": "analysis"},
    },
    "cleanup-old-metrics": {
        "task": "cleanup_old_metrics",
        "schedule": crontab(hour=4, minute=0, day_of_week=0),  # Run weekly on Sunday at 4 AM
        "options": {"queue": "maintenance"},
    },
}

# Configure task routing
celery_app.conf.task_routes = {
    "src.app.tasks.scraping_tasks.*": {"queue": "scraping"},
    "src.app.tasks.product_tasks.*": {"queue": "monitoring"},
    "src.app.tasks.analysis_tasks.*": {"queue": "analysis"},
}
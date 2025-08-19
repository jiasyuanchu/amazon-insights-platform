#!/usr/bin/env python3
"""Test script to send a Celery task"""

from src.app.tasks.celery_app import celery_app

# Send a test task using the registered task name
result = celery_app.send_task('monitor_price_changes')
print(f'Task ID: {result.id}')
print(f'Task Status: {result.status}')

# You can also send other tasks
# result2 = celery_app.send_task('scrape_single_product', args=['B08N5WRWNW'])
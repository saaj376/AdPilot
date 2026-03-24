from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

_scheduler: AsyncIOScheduler | None = None


async def _daily_maintenance_job() -> None:
	"""Placeholder daily maintenance hook for post-launch automation."""
	# Keep startup stable even when no recurring work is configured yet.
	return


def start_scheduler() -> None:
	"""Start the shared APScheduler instance if it is not already running."""
	global _scheduler

	if _scheduler is not None and _scheduler.running:
		return

	_scheduler = AsyncIOScheduler(timezone="UTC")
	_scheduler.add_job(
		_daily_maintenance_job,
		trigger=CronTrigger(hour=0, minute=0),
		id="daily_maintenance",
		replace_existing=True,
	)
	_scheduler.start()
	print("Scheduler started.")


def stop_scheduler() -> None:
	"""Stop the shared APScheduler instance if it is running."""
	global _scheduler

	if _scheduler is None:
		return

	if _scheduler.running:
		_scheduler.shutdown(wait=False)
		print("Scheduler stopped.")

	_scheduler = None

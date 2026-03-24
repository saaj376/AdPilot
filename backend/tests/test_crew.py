import core.scheduler as scheduler


class _FakeScheduler:
	def __init__(self, timezone=None):
		self.timezone = timezone
		self.running = False
		self.jobs = []

	def add_job(self, func, trigger, id, replace_existing):
		self.jobs.append(
			{
				"func": func,
				"trigger": trigger,
				"id": id,
				"replace_existing": replace_existing,
			}
		)

	def start(self):
		self.running = True

	def shutdown(self, wait=False):
		self.running = False


def test_scheduler_start_and_stop(monkeypatch):
	monkeypatch.setattr(scheduler, "AsyncIOScheduler", _FakeScheduler)
	scheduler._scheduler = None

	scheduler.start_scheduler()

	assert scheduler._scheduler is not None
	assert scheduler._scheduler.running is True
	assert len(scheduler._scheduler.jobs) == 1
	assert scheduler._scheduler.jobs[0]["id"] == "daily_maintenance"

	scheduler.stop_scheduler()
	assert scheduler._scheduler is None


def test_scheduler_start_is_idempotent(monkeypatch):
	monkeypatch.setattr(scheduler, "AsyncIOScheduler", _FakeScheduler)
	scheduler._scheduler = None

	scheduler.start_scheduler()
	first = scheduler._scheduler
	scheduler.start_scheduler()
	second = scheduler._scheduler

	assert first is second
	assert first.running is True

	scheduler.stop_scheduler()

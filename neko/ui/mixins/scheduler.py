"""Non-blocking download task scheduler.

Replaces the join()-based queue processing with an event-queue + after() poll model.
Download threads push events to a queue; the UI polls it every 100ms.
"""

import queue
import threading
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskEvent:
    """An event pushed from a worker thread to the UI."""
    __slots__ = ("task_id", "kind", "data")

    def __init__(self, task_id, kind, data=None):
        self.task_id = task_id
        self.kind = kind      # "status", "progress", "log", "done"
        self.data = data or {}


class TaskScheduler:
    """Manages concurrent download workers without blocking the UI thread.

    Usage:
        scheduler = TaskScheduler(max_workers=2, ui_callback=self._on_task_event, done_callback=self._on_all_done)
        scheduler.submit(task_id, callable)

    The ui_callback is called on the main thread via root.after() for each event.
    The done_callback fires once all submitted tasks complete.
    """

    def __init__(self, max_workers, ui_callback, done_callback=None, after_fn=None):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._events = queue.Queue()
        self._ui_callback = ui_callback
        self._done_callback = done_callback
        self._after = after_fn  # typically root.after
        self._pending = 0
        self._lock = threading.Lock()
        self._cancelled = False
        self._polling = False

    # ── Public API ─────────────────────────────────────────────

    def submit(self, task_id, fn, *args, **kwargs):
        """Submit a callable as a background task. fn receives task_id as first arg."""
        with self._lock:
            self._pending += 1
        self._executor.submit(self._run_task, task_id, fn, *args, **kwargs)

    def cancel(self):
        """Signal cancellation; running tasks should check is_cancelled()."""
        self._cancelled = True

    @property
    def is_cancelled(self):
        return self._cancelled

    def push_event(self, task_id, kind, data=None):
        """Called from worker threads to send an event to the UI."""
        self._events.put(TaskEvent(task_id, kind, data))

    def start_polling(self, root, interval_ms=100):
        """Start the UI poll loop. Call once from the main thread."""
        self._root = root
        self._interval = interval_ms
        self._polling = True
        root.after(interval_ms, self._poll)

    def shutdown(self):
        """Shut down the executor. Non-blocking."""
        self._executor.shutdown(wait=False, cancel_futures=True)

    # ── Internal ───────────────────────────────────────────────

    def _run_task(self, task_id, fn, *args, **kwargs):
        try:
            fn(task_id, *args, **kwargs)
        except Exception as e:
            self.push_event(task_id, "status", {"state": "error", "message": str(e)})
        finally:
            with self._lock:
                self._pending -= 1
                remaining = self._pending
            self.push_event(task_id, "done", {"remaining": remaining})
            if remaining <= 0:
                self._events.put(TaskEvent("__all__", "all_done"))

    def _poll(self):
        """Drain the event queue and dispatch to UI callback. Runs on main thread."""
        try:
            for _ in range(50):  # process up to 50 events per tick
                try:
                    evt = self._events.get_nowait()
                except queue.Empty:
                    break

                if evt.kind == "all_done":
                    if self._done_callback:
                        self._done_callback()
                    self._polling = False
                    return  # stop polling

                self._ui_callback(evt)
        except Exception as e:
            logger.error(f"Event poll error: {e}")
        finally:
            if self._polling and self._after:
                self._after(self._interval, self._poll)

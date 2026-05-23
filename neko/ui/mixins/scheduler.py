"""Non-blocking download task scheduler with cancellation support.

Replaces the join()-based queue processing with an event-queue + after() poll model.
Download threads push events to a queue; the UI polls it every 100ms.
Each task can be cancelled — its subprocess is killed and status set to 'cancelled'.
"""

import os
import queue
import threading
import logging
import subprocess
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

    Each submitted task gets a cancellation token (threading.Event).
    The worker's subprocess handle is stored so cancel_task() can kill it.
    """

    def __init__(self, max_workers, ui_callback, done_callback=None, after_fn=None):
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._events = queue.Queue()
        self._ui_callback = ui_callback
        self._done_callback = done_callback
        self._after = after_fn
        self._pending = 0
        self._lock = threading.Lock()
        self._cancelled_all = False
        self._polling = False
        # task_id -> threading.Event (set = cancelled)
        self._cancel_flags = {}
        # task_id -> subprocess.Popen (for killing)
        self._processes = {}

    # ── Public API ─────────────────────────────────────────────

    def submit(self, task_id, fn, *args, **kwargs):
        """Submit a callable as a background task. fn receives task_id as first arg."""
        cancel_flag = threading.Event()
        with self._lock:
            self._pending += 1
            self._cancel_flags[task_id] = cancel_flag
        self._executor.submit(self._run_task, task_id, cancel_flag, fn, *args, **kwargs)

    def register_process(self, task_id, popen):
        """Store a Popen handle so cancel_task() can kill it."""
        self._processes[task_id] = popen

    def unregister_process(self, task_id):
        """Remove a Popen handle after the process ends."""
        self._processes.pop(task_id, None)

    def is_task_cancelled(self, task_id):
        """Check if a specific task has been cancelled."""
        flag = self._cancel_flags.get(task_id)
        return flag is not None and flag.is_set()

    def cancel_task(self, task_id):
        """Cancel a single task: set its flag and kill its subprocess."""
        flag = self._cancel_flags.get(task_id)
        if flag:
            flag.set()
        self._kill_process(task_id)

    def cancel_all(self):
        """Cancel all tasks."""
        self._cancelled_all = True
        with self._lock:
            for flag in self._cancel_flags.values():
                flag.set()
        for task_id in list(self._processes.keys()):
            self._kill_process(task_id)

    @property
    def is_cancelled_all(self):
        return self._cancelled_all

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

    # ── Process killing ─────────────────────────────────────────

    def _kill_process(self, task_id):
        """Kill a subprocess and its children. Cross-platform."""
        p = self._processes.pop(task_id, None)
        if p is None:
            return
        try:
            if p.poll() is not None:
                return  # already exited
            if os.name == 'nt':
                # Windows: kill process tree via taskkill
                try:
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(p.pid)],
                        capture_output=True,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                    )
                except Exception:
                    p.kill()
            else:
                # Unix: send SIGTERM, then SIGKILL after 3s
                p.terminate()
                try:
                    p.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    p.kill()
        except Exception as e:
            logger.error(f"Failed to kill process {task_id}: {e}")

    # ── Internal ───────────────────────────────────────────────

    def _run_task(self, task_id, cancel_flag, fn, *args, **kwargs):
        try:
            if not cancel_flag.is_set():
                fn(task_id, *args, **kwargs)
        except Exception as e:
            if not cancel_flag.is_set():
                self.push_event(task_id, "status", {"state": "error", "message": str(e)})
        finally:
            self.unregister_process(task_id)
            with self._lock:
                self._pending -= 1
                remaining = self._pending
                self._cancel_flags.pop(task_id, None)
            self.push_event(task_id, "done", {"remaining": remaining})
            if remaining <= 0:
                self._events.put(TaskEvent("__all__", "all_done"))

    def _poll(self):
        """Drain the event queue and dispatch to UI callback. Runs on main thread."""
        try:
            for _ in range(50):
                try:
                    evt = self._events.get_nowait()
                except queue.Empty:
                    break

                if evt.kind == "all_done":
                    if self._done_callback:
                        self._done_callback()
                    self._polling = False
                    return

                self._ui_callback(evt)
        except Exception as e:
            logger.error(f"Event poll error: {e}")
        finally:
            if self._polling and self._after:
                self._after(self._interval, self._poll)

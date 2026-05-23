import os
import subprocess
import threading
import traceback
import logging

logger = logging.getLogger(__name__)


def safe_run(func):
    """Decorator that catches exceptions and logs them to the neko log box."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self_obj = args[0] if args else None
            func_name = func.__name__
            print(f"❌ Error inside [{func_name}]: {e}")
            print(traceback.format_exc())
            if self_obj and hasattr(self_obj, 'log'):
                err_msg = str(e)
                self_obj.log(f"💥 崩溃拦截 [{func_name}]: {err_msg[:60]}...", "sad")
            return False
    return wrapper


def show_windows_toast(title, msg):
    """Show a Windows toast notification in a background thread."""
    def _run():
        ps_script = f"""
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] > $null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $textNodes = $template.GetElementsByTagName("text")
        $textNodes.Item(0).AppendChild($template.CreateTextNode('{title}')) > $null
        $textNodes.Item(1).AppendChild($template.CreateTextNode('{msg}')) > $null
        $notifier = [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("Neko Downloader")
        $notification = [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType = WindowsRuntime]::new($template)
        $notifier.Show($notification)
        """
        try:
            subprocess.run(
                ["powershell", "-Command", ps_script],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
        except Exception:
            pass
    threading.Thread(target=_run, daemon=True).start()

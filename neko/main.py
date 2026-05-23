import sys
import logging
import tkinter as tk
from tkinter import messagebox

from .core.cache import CacheManager
from .ui.loading import UILoader

logger = logging.getLogger(__name__)


def main():
    """Main entry point — can be called from the package or the wrapper script."""
    try:
        cache_manager = CacheManager()

        if not cache_manager.is_cache_valid():
            logger.info("检测到代码更新，清除旧缓存")
            cache_manager.clear_cache()

        ui_loader = UILoader(cache_manager)
        ui_loader.start_loading()

    except Exception as e:
        logger.error(f"程序启动失败: {e}")
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("启动失败", f"程序启动失败:\n{str(e)}")
        root.destroy()
        sys.exit(1)


if __name__ == "__main__":
    main()

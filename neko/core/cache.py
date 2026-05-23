import os
import hashlib
import pickle
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    def __init__(self, cache_dir="cache"):
        self.cache_dir = cache_dir
        self.cache_file = os.path.join(cache_dir, "ui_cache.pkl")
        self.code_hash_file = os.path.join(cache_dir, "code_hash.txt")
        os.makedirs(cache_dir, exist_ok=True)

    def get_code_hash(self):
        try:
            neko_dir = os.path.dirname(os.path.dirname(__file__))
            h = hashlib.md5()
            for root, _, files in os.walk(neko_dir):
                for name in sorted(files):
                    if name.endswith('.py'):
                        with open(os.path.join(root, name), 'rb') as f:
                            h.update(f.read())
            return h.hexdigest()
        except Exception as e:
            logger.error(f"获取代码哈希失败: {e}")
            return None

    def is_cache_valid(self):
        try:
            if not os.path.exists(self.cache_file) or not os.path.exists(self.code_hash_file):
                return False
            with open(self.code_hash_file, 'r') as f:
                cached_hash = f.read().strip()
            current_hash = self.get_code_hash()
            return cached_hash == current_hash and current_hash is not None
        except Exception as e:
            logger.error(f"检查缓存有效性失败: {e}")
            return False

    def save_cache(self, data):
        try:
            with open(self.cache_file, 'wb') as f:
                pickle.dump(data, f)
            current_hash = self.get_code_hash()
            if current_hash:
                with open(self.code_hash_file, 'w') as f:
                    f.write(current_hash)
            logger.info("缓存保存成功")
            return True
        except Exception as e:
            logger.error(f"保存缓存失败: {e}")
            return False

    def load_cache(self):
        try:
            if not self.is_cache_valid():
                return None
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
            logger.info("缓存加载成功")
            return data
        except Exception as e:
            logger.error(f"加载缓存失败: {e}")
            return None

    def clear_cache(self):
        try:
            if os.path.exists(self.cache_file):
                os.remove(self.cache_file)
            if os.path.exists(self.code_hash_file):
                os.remove(self.code_hash_file)
            logger.info("缓存清除成功")
        except Exception as e:
            logger.error(f"清除缓存失败: {e}")

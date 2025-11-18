"""
ロギング機能モジュール
"""

import logging
from pathlib import Path
from datetime import datetime


class AppLogger:
	"""アプリケーション用ロガー"""
	
	def __init__(self, name: str = "JourneyMap", log_dir: Path = None):
		"""
		ロガーを初期化
		
		Args:
			name: ロガー名
			log_dir: ログファイル保存先（Noneの場合はdata/logs/）
		"""
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)
		
		# ログディレクトリ
		if log_dir is None:
			log_dir = Path("data/logs")
		log_dir.mkdir(parents=True, exist_ok=True)
		
		# ログファイル名（日付付き）
		log_file = log_dir / f"journeymap_{datetime.now().strftime('%Y%m%d')}.log"
		
		# ファイルハンドラ
		file_handler = logging.FileHandler(log_file, encoding='utf-8')
		file_handler.setLevel(logging.DEBUG)
		
		# コンソールハンドラ
		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.INFO)
		
		# フォーマット
		formatter = logging.Formatter(
			'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
		)
		file_handler.setFormatter(formatter)
		console_handler.setFormatter(formatter)
		
		# ハンドラを追加
		if not self.logger.handlers:
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)
	
	def debug(self, message: str):
		"""デバッグログ"""
		self.logger.debug(message)
	
	def info(self, message: str):
		"""情報ログ"""
		self.logger.info(message)
	
	def warning(self, message: str):
		"""警告ログ"""
		self.logger.warning(message)
	
	def error(self, message: str, exc_info: bool = True):
		"""エラーログ"""
		self.logger.error(message, exc_info=exc_info)
	
	def critical(self, message: str, exc_info: bool = True):
		"""致命的エラーログ"""
		self.logger.critical(message, exc_info=exc_info)


# グローバルロガーインスタンス
_logger_instance = None


def get_logger() -> AppLogger:
	"""グローバルロガーを取得"""
	global _logger_instance
	if _logger_instance is None:
		_logger_instance = AppLogger()
	return _logger_instance


# テスト用コード
if __name__ == "__main__":
	logger = get_logger()
	
	logger.debug("デバッグメッセージ")
	logger.info("情報メッセージ")
	logger.warning("警告メッセージ")
	
	try:
		1 / 0
	except Exception:
		logger.error("エラーが発生しました", exc_info=True)
"""
ロギング機能モジュール
"""

import logging
from pathlib import Path
from datetime import datetime


class AppLogger:
	"""アプリケーション用ロガー"""
	
	def __init__(self, name: str = "JourneyMap", log_dir: Path | None = None):
		"""
		ロガーを初期化
		
		Args:
			name: ロガー名
			log_dir: ログファイル保存先（Noneの場合はdata/logs/）
		"""
		self.logger = logging.getLogger(name)
		self.logger.setLevel(logging.DEBUG)
		
		# ログディレクトリ
		if log_dir is None:
			log_dir = Path("data/logs")
		log_dir.mkdir(parents=True, exist_ok=True)
		
		# ログファイル名（日付付き）
		log_file = log_dir / f"journeymap_{datetime.now().strftime('%Y%m%d')}.log"
		
		# ファイルハンドラ
		file_handler = logging.FileHandler(log_file, encoding='utf-8')
		file_handler.setLevel(logging.DEBUG)
		
		# コンソールハンドラ
		console_handler = logging.StreamHandler()
		console_handler.setLevel(logging.INFO)
		
		# フォーマット
		formatter = logging.Formatter(
			'%(asctime)s - %(name)s - %(levelname)s - %(message)s',
			datefmt='%Y-%m-%d %H:%M:%S'
		)
		file_handler.setFormatter(formatter)
		console_handler.setFormatter(formatter)
		
		# ハンドラを追加（多重追加防止）
		if not self.logger.handlers:
			self.logger.addHandler(file_handler)
			self.logger.addHandler(console_handler)
	
	def debug(self, message: str):
		self.logger.debug(message)
	
	def info(self, message: str):
		self.logger.info(message)
	
	def warning(self, message: str):
		self.logger.warning(message)
	
	def error(self, message: str, exc_info: bool = True):
		self.logger.error(message, exc_info=exc_info)
	
	def critical(self, message: str, exc_info: bool = True):
		self.logger.critical(message, exc_info=exc_info)


# グローバルロガーインスタンス
_logger_instance: AppLogger | None = None


def get_logger() -> AppLogger:
	"""グローバルロガーを取得"""
	global _logger_instance
	if _logger_instance is None:
		_logger_instance = AppLogger()
	return _logger_instance


# テスト用コード
if __name__ == "__main__":
	logger = get_logger()
	logger.debug("デバッグメッセージ")
	logger.info("情報メッセージ")
	logger.warning("警告メッセージ")
	try:
		1 / 0
	except Exception:
		logger.error("エラーが発生しました", exc_info=True)


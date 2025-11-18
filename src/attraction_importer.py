"""
観光地データインポートモジュール
"""

import csv
from pathlib import Path
from typing import List, Dict, Any
from src.database import Database
from src.logger import get_logger


class AttractionImporter:
	"""観光地データインポートクラス"""
	
	def __init__(self):
		self.logger = get_logger()
	
	def import_from_csv(self, csv_path: Path) -> int:
		"""
		CSVファイルから観光地データをインポート
		
		Args:
			csv_path: CSVファイルのパス
			
		Returns:
			インポートした件数
		"""
		try:
			if not csv_path.exists():
				self.logger.error(f"CSVファイルが見つかりません: {csv_path}")
				return 0
			
			db = Database()
			db.initialize()
			
			imported = 0
			skipped = 0
			
			with open(csv_path, 'r', encoding='utf-8') as f:
				reader = csv.DictReader(f)
				
				for row in reader:
					try:
						attraction = {
							'name': row['name'],
							'name_en': row.get('name_en'),
							'category': row.get('category'),
							'latitude': float(row['latitude']),
							'longitude': float(row['longitude']),
							'description': row.get('description'),
							'rating': float(row['rating']) if row.get('rating') else None,
							'prefecture': row.get('prefecture'),
							'city': row.get('city'),
							'source': 'csv_import'
						}
						
						db.insert_attraction(attraction)
						imported += 1
						
					except Exception as e:
						self.logger.warning(f"データスキップ: {row.get('name')} - {e}")
						skipped += 1
			
			self.logger.info(f"観光地インポート完了: {imported}件登録、{skipped}件スキップ")
			return imported
			
		except Exception as e:
			self.logger.error("CSVインポートエラー")
			raise


# テスト用コード
if __name__ == "__main__":
	importer = AttractionImporter()
	csv_path = Path("data/attractions_japan.csv")
	
	count = importer.import_from_csv(csv_path)
	print(f"インポート完了: {count}件")


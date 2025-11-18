"""

JourneyMap データベース管理モジュール

SQLite を使用して写真・動画のメタデータを管理

"""

import sqlite3
import os
from pathlib import Path
from src.logger import get_logger
import streamlit as st
from functools import lru_cache
import hashlib
import json
from typing import List, Dict, Any


class Database:
	"""SQLite データベース管理クラス"""
	
	def __init__(self, db_path="data/journeymap.db"):
		"""
		データベース初期化
		
		Args:
			db_path (str): データベースファイルのパス
		"""
		# プロジェクトルートからの相対パスを絶対パスに変換
		self.db_path = Path(__file__).parent.parent / db_path
		self.db_path.parent.mkdir(parents=True, exist_ok=True)
		self.conn = None
		self.logger = get_logger()
	
	def connect(self):
		"""データベースに接続"""
		try:
			self.conn = sqlite3.connect(self.db_path)
			self.conn.row_factory = sqlite3.Row  # 辞書形式で結果を取得
			self.logger.debug(f"データベース接続: {self.db_path}")
			return self.conn
		except Exception as e:
			self.logger.error(f"データベース接続エラー: {self.db_path}")
			raise
	
	def close(self):
		"""データベース接続を閉じる"""
		try:
			if self.conn:
				self.conn.close()
				self.conn = None
				self.logger.debug("データベース接続を閉じました")
		except Exception as e:
			self.logger.error("データベース切断エラー")
	
	def initialize(self):
		"""
		データベースを初期化（テーブル作成）
		既存のテーブルがある場合は何もしない
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			# photosテーブル作成
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS photos (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					file_path TEXT NOT NULL UNIQUE,
					file_type TEXT NOT NULL,
					latitude REAL,
					longitude REAL,
					timestamp TEXT,
					created_at TEXT DEFAULT CURRENT_TIMESTAMP,
					location_name TEXT
				)
			""")
			
			# インデックス作成（検索高速化）
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_timestamp 
				ON photos(timestamp)
			""")
			
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_location 
				ON photos(latitude, longitude)
			""")
			
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_file_type 
				ON photos(file_type)
			""")
			
			self.conn.commit()
			cursor.close()
			print("✅ データベース初期化完了")
			print(f"📁 データベースファイル: {self.db_path}")
			
			# マイグレーション実行（冪等）
			self.migrate_add_location_name()
			# 観光地テーブルを作成（冪等）
			self.create_attractions_table()
			# ウィッシュリストテーブルを作成（冪等）
			self.create_wishlist_table()
			# 旅程テーブルを作成（冪等）
			self.create_itinerary_table()
		except Exception as e:
			self.logger.error("データベース初期化エラー")
			raise
	
	def create_attractions_table(self):
		"""観光地テーブルを作成"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS attractions (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL,
					name_en TEXT,
					category TEXT,
					latitude REAL NOT NULL,
					longitude REAL NOT NULL,
					description TEXT,
					rating REAL,
					prefecture TEXT,
					city TEXT,
					visited BOOLEAN DEFAULT 0,
					visit_date TEXT,
					source TEXT,
					created_at TEXT DEFAULT CURRENT_TIMESTAMP
				)
			""")
			
			# インデックスを作成
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_attractions_location 
				ON attractions(latitude, longitude)
			""")
			
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_attractions_category 
				ON attractions(category)
			""")
			
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_attractions_visited 
				ON attractions(visited)
			""")
			
			self.conn.commit()
			self.logger.info("観光地テーブルを作成しました")
			self.close()
			
		except Exception as e:
			self.logger.error("観光地テーブル作成エラー")
			raise
	
	def create_wishlist_table(self):
		"""ウィッシュリストテーブルを作成"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS wishlist (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					attraction_id INTEGER NOT NULL,
					priority INTEGER DEFAULT 3,
					notes TEXT,
					planned_date TEXT,
					created_at TEXT DEFAULT CURRENT_TIMESTAMP,
					updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
					FOREIGN KEY (attraction_id) REFERENCES attractions(id),
					UNIQUE(attraction_id)
				)
			""")
			
			# インデックスを作成
			cursor.execute("""
				CREATE INDEX IF NOT EXISTS idx_wishlist_priority 
				ON wishlist(priority DESC)
			""")
			
			self.conn.commit()
			self.logger.info("ウィッシュリストテーブルを作成しました")
			self.close()
			
		except Exception as e:
			self.logger.error("ウィッシュリストテーブル作成エラー")
			raise
	
	def create_itinerary_table(self):
		"""旅程テーブルを作成"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS itineraries (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					name TEXT NOT NULL,
					description TEXT,
					days INTEGER DEFAULT 1,
					total_distance REAL,
					created_at TEXT DEFAULT CURRENT_TIMESTAMP
				)
			""")
			
			cursor.execute("""
				CREATE TABLE IF NOT EXISTS itinerary_items (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					itinerary_id INTEGER NOT NULL,
					day_number INTEGER DEFAULT 1,
					sequence_number INTEGER NOT NULL,
					attraction_id INTEGER,
					wishlist_id INTEGER,
					notes TEXT,
					FOREIGN KEY (itinerary_id) REFERENCES itineraries(id),
					FOREIGN KEY (attraction_id) REFERENCES attractions(id),
					FOREIGN KEY (wishlist_id) REFERENCES wishlist(id)
				)
			""")
			
			self.conn.commit()
			self.logger.info("旅程テーブルを作成しました")
			self.close()
			
		except Exception as e:
			self.logger.error("旅程テーブル作成エラー")
			raise
	
	def migrate_add_location_name(self):
		"""location_name カラムを追加するマイグレーション"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			# カラムが存在するか確認
			cursor.execute("PRAGMA table_info(photos)")
			columns = [row[1] for row in cursor.fetchall()]
			
			if 'location_name' not in columns:
				cursor.execute("""
					ALTER TABLE photos
					ADD COLUMN location_name TEXT
				""")
				self.conn.commit()
				self.logger.info("location_name カラムを追加しました")
			else:
				self.logger.debug("location_name カラムは既に存在します")
			
			self.close()
		except Exception as e:
			self.logger.error("マイグレーションエラー")
			raise
	
	@staticmethod
	def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
		"""
		2地点間の距離を計算（ハバーサイン公式）
		
		Args:
			lat1, lon1: 地点1の緯度経度
			lat2, lon2: 地点2の緯度経度
			
		Returns:
			距離（km）
		"""
		from math import radians, sin, cos, sqrt, atan2
		
		# 地球の半径（km）
		R = 6371.0
		
		# ラジアンに変換
		lat1_rad = radians(lat1)
		lon1_rad = radians(lon1)
		lat2_rad = radians(lat2)
		lon2_rad = radians(lon2)
		
		# 差分
		dlat = lat2_rad - lat1_rad
		dlon = lon2_rad - lon1_rad
		
		# ハバーサイン公式
		a = sin(dlat / 2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon / 2)**2
		c = 2 * atan2(sqrt(a), sqrt(1 - a))
		
		distance = R * c
		return distance
	
	def auto_mark_visited_attractions(self, threshold_km: float = 0.5) -> int:
		"""
		写真の位置情報から観光地を自動的に訪問済みにする
		
		Args:
			threshold_km: 判定距離の閾値（km）
			
		Returns:
			更新した件数
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			# 写真の位置情報を取得
			cursor.execute("""
				SELECT DISTINCT latitude, longitude, timestamp
				FROM photos
				WHERE latitude IS NOT NULL AND longitude IS NOT NULL
				ORDER BY timestamp
			""")
			
			photo_locations = cursor.fetchall()
			
			if not photo_locations:
				self.logger.info("写真データがないため、訪問済み判定をスキップ")
				return 0
			
			# 未訪問の観光地を取得
			cursor.execute("""
				SELECT id, name, latitude, longitude
				FROM attractions
				WHERE visited = 0
			""")
			
			unvisited_attractions = cursor.fetchall()
			
			updated = 0
			
			for attraction in unvisited_attractions:
				attraction_id = attraction['id']
				attraction_name = attraction['name']
				attraction_lat = attraction['latitude']
				attraction_lon = attraction['longitude']
				
				# 各写真の位置と比較
				for photo in photo_locations:
					photo_lat = photo['latitude']
					photo_lon = photo['longitude']
					photo_timestamp = photo['timestamp']
					
					# 距離を計算
					distance = self.calculate_distance(
						attraction_lat, attraction_lon,
						photo_lat, photo_lon
					)
					
					# 閾値以内なら訪問済みにする
					if distance <= threshold_km:
						cursor.execute("""
							UPDATE attractions
							SET visited = 1, visit_date = ?
							WHERE id = ?
						""", (photo_timestamp, attraction_id))
						
						self.logger.info(f"観光地を訪問済みに設定: {attraction_name} (距離: {distance:.2f}km)")
						updated += 1
						break  # この観光地は完了
			
			self.conn.commit()
			self.close()
			
			self.logger.info(f"自動訪問済み判定完了: {updated}件更新")
			return updated
			
		except Exception as e:
			self.logger.error("自動訪問済み判定エラー")
			raise
	def insert_attraction(self, attraction: Dict[str, Any]) -> int:
		"""
		観光地を登録
		
		Args:
			attraction: 観光地データ
			
		Returns:
			登録したID
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				INSERT INTO attractions 
				(name, name_en, category, latitude, longitude, description, 
				 rating, prefecture, city, source)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
			""", (
				attraction['name'],
				attraction.get('name_en'),
				attraction.get('category'),
				attraction['latitude'],
				attraction['longitude'],
				attraction.get('description'),
				attraction.get('rating'),
				attraction.get('prefecture'),
				attraction.get('city'),
				attraction.get('source', 'manual')
			))
			
			attraction_id = cursor.lastrowid
			self.conn.commit()
			self.close()
			
			self.logger.info(f"観光地を登録: {attraction['name']}")
			return attraction_id
			
		except Exception as e:
			self.logger.error(f"観光地登録エラー: {attraction.get('name')}")
			raise
	
	def get_all_attractions(self, category: str = None, visited: bool = None) -> List[Dict[str, Any]]:
		"""
		観光地を取得
		
		Args:
			category: カテゴリでフィルタ（Noneの場合は全て）
			visited: 訪問済みでフィルタ（Noneの場合は全て）
			
		Returns:
			観光地データのリスト
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			query = "SELECT * FROM attractions WHERE 1=1"
			params = []
			
			if category:
				query += " AND category = ?"
				params.append(category)
			
			if visited is not None:
				query += " AND visited = ?"
				params.append(1 if visited else 0)
			
			query += " ORDER BY name"
			
			cursor.execute(query, params)
			rows = cursor.fetchall()
			self.close()
			
			attractions = []
			for row in rows:
				attractions.append({
					'id': row['id'],
					'name': row['name'],
					'name_en': row['name_en'],
					'category': row['category'],
					'latitude': row['latitude'],
					'longitude': row['longitude'],
					'description': row['description'],
					'rating': row['rating'],
					'prefecture': row['prefecture'],
					'city': row['city'],
					'visited': bool(row['visited']),
					'visit_date': row['visit_date'],
					'source': row['source'],
					'created_at': row['created_at']
				})
			
			return attractions
			
		except Exception as e:
			self.logger.error("観光地取得エラー")
			raise
	
	def mark_attraction_visited(self, attraction_id: int, visit_date: str = None):
		"""
		観光地を訪問済みにする
		
		Args:
			attraction_id: 観光地ID
			visit_date: 訪問日（Noneの場合は現在日時）
		"""
		try:
			from datetime import datetime
			
			if visit_date is None:
				visit_date = datetime.now().isoformat()
			
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				UPDATE attractions
				SET visited = 1, visit_date = ?
				WHERE id = ?
			""", (visit_date, attraction_id))
			
			self.conn.commit()
			self.close()
			
			self.logger.info(f"観光地を訪問済みに設定: ID={attraction_id}")
			
		except Exception as e:
			self.logger.error(f"訪問済み設定エラー: ID={attraction_id}")
			raise
	
	@st.cache_data(ttl=300)
	def get_attractions_cached(_self, category: str = None, visited: bool = None) -> List[Dict[str, Any]]:
		"""観光地を取得（キャッシュ版）"""
		return _self.get_all_attractions(category=category, visited=visited)
	
	def add_to_wishlist(
		self,
		attraction_id: int,
		priority: int = 3,
		notes: str = None,
		planned_date: str = None
	) -> int:
		"""
		ウィッシュリストに追加
		
		Args:
			attraction_id: 観光地ID
			priority: 優先度（1-5、5が最高）
			notes: メモ
			planned_date: 訪問予定日
			
		Returns:
			ウィッシュリストID
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				INSERT INTO wishlist (attraction_id, priority, notes, planned_date)
				VALUES (?, ?, ?, ?)
			""", (attraction_id, priority, notes, planned_date))
			
			wishlist_id = cursor.lastrowid
			self.conn.commit()
			self.close()
			
			self.logger.info(f"ウィッシュリストに追加: attraction_id={attraction_id}")
			return wishlist_id
			
		except Exception as e:
			self.logger.error(f"ウィッシュリスト追加エラー: attraction_id={attraction_id}")
			raise
	
	def remove_from_wishlist(self, wishlist_id: int):
		"""
		ウィッシュリストから削除
		
		Args:
			wishlist_id: ウィッシュリストID
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("DELETE FROM wishlist WHERE id = ?", (wishlist_id,))
			
			self.conn.commit()
			self.close()
			
			self.logger.info(f"ウィッシュリストから削除: id={wishlist_id}")
			
		except Exception as e:
			self.logger.error(f"ウィッシュリスト削除エラー: id={wishlist_id}")
			raise
	
	def update_wishlist_item(
		self,
		wishlist_id: int,
		priority: int = None,
		notes: str = None,
		planned_date: str = None
	):
		"""
		ウィッシュリストアイテムを更新
		
		Args:
			wishlist_id: ウィッシュリストID
			priority: 優先度
			notes: メモ
			planned_date: 訪問予定日
		"""
		try:
			from datetime import datetime
			
			self.connect()
			cursor = self.conn.cursor()
			
			updates = []
			params = []
			
			if priority is not None:
				updates.append("priority = ?")
				params.append(priority)
			
			if notes is not None:
				updates.append("notes = ?")
				params.append(notes)
			
			if planned_date is not None:
				updates.append("planned_date = ?")
				params.append(planned_date)
			
			if updates:
				updates.append("updated_at = ?")
				params.append(datetime.now().isoformat())
				
				query = f"UPDATE wishlist SET {', '.join(updates)} WHERE id = ?"
				params.append(wishlist_id)
				
				cursor.execute(query, params)
				self.conn.commit()
			
			self.close()
			self.logger.info(f"ウィッシュリストを更新: id={wishlist_id}")
			
		except Exception as e:
			self.logger.error(f"ウィッシュリスト更新エラー: id={wishlist_id}")
			raise
	
	def get_wishlist(self, order_by: str = 'priority') -> List[Dict[str, Any]]:
		"""
		ウィッシュリストを取得
		
		Args:
			order_by: ソート順（'priority', 'created_at', 'name'）
			
		Returns:
			ウィッシュリストアイテムのリスト
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			# ソート順を決定
			if order_by == 'priority':
				order_clause = "w.priority DESC, a.name"
			elif order_by == 'created_at':
				order_clause = "w.created_at DESC"
			elif order_by == 'name':
				order_clause = "a.name"
			else:
				order_clause = "w.priority DESC"
			
			cursor.execute(f"""
				SELECT 
					w.id,
					w.attraction_id,
					w.priority,
					w.notes,
					w.planned_date,
					w.created_at,
					w.updated_at,
					a.name,
					a.name_en,
					a.category,
					a.latitude,
					a.longitude,
					a.description,
					a.rating,
					a.prefecture,
					a.city
				FROM wishlist w
				JOIN attractions a ON w.attraction_id = a.id
				ORDER BY {order_clause}
			""")
			
			rows = cursor.fetchall()
			self.close()
			
			wishlist = []
			for row in rows:
				wishlist.append({
					'id': row['id'],
					'attraction_id': row['attraction_id'],
					'priority': row['priority'],
					'notes': row['notes'],
					'planned_date': row['planned_date'],
					'created_at': row['created_at'],
					'updated_at': row['updated_at'],
					'name': row['name'],
					'name_en': row['name_en'],
					'category': row['category'],
					'latitude': row['latitude'],
					'longitude': row['longitude'],
					'description': row['description'],
					'rating': row['rating'],
					'prefecture': row['prefecture'],
					'city': row['city']
				})
			
			return wishlist
			
		except Exception as e:
			self.logger.error("ウィッシュリスト取得エラー")
			raise
	
	def is_in_wishlist(self, attraction_id: int) -> bool:
		"""
		観光地がウィッシュリストに含まれているか確認
		
		Args:
			attraction_id: 観光地ID
			
		Returns:
			ウィッシュリストに含まれている場合True
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			cursor.execute("""
				SELECT COUNT(*) FROM wishlist WHERE attraction_id = ?
			""", (attraction_id,))
			
			count = cursor.fetchone()[0]
			self.close()
			
			return count > 0
			
		except Exception as e:
			self.logger.error(f"ウィッシュリスト確認エラー: attraction_id={attraction_id}")
			raise
	
	@st.cache_data(ttl=300)
	def get_wishlist_cached(_self, order_by: str = 'priority') -> List[Dict[str, Any]]:
		"""ウィッシュリストを取得（キャッシュ版）"""
		return _self.get_wishlist(order_by=order_by)
	@staticmethod
	def _calculate_db_hash(db_path: str) -> str:
		"""
		データベースファイルのハッシュを計算
		
		Args:
			db_path: データベースファイルのパス
			
		Returns:
			ハッシュ値
		"""
		try:
			from pathlib import Path as _P
			db_file = _P(db_path)
			
			if not db_file.exists():
				return "no_db"
			
			# ファイルの最終更新時刻とサイズからハッシュを生成
			stat = db_file.stat()
			hash_input = f"{stat.st_mtime}_{stat.st_size}"
			return hashlib.md5(hash_input.encode()).hexdigest()
		except Exception:
			return "error"
	
	def get_table_info(self):
		"""
		テーブル情報を取得（デバッグ用）
		
		Returns:
			list: テーブルのカラム情報
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			cursor.execute("PRAGMA table_info(photos)")
			columns = cursor.fetchall()
			cursor.close()
			return columns
		except Exception as e:
			self.logger.error("テーブル情報取得エラー")
			return []
	
	def count_photos(self):
		"""
		登録済み写真の件数を取得
		
		Returns:
			int: 写真の件数
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			cursor.execute("SELECT COUNT(*) FROM photos")
			count = cursor.fetchone()[0]
			cursor.close()
			return count
		except Exception as e:
			self.logger.error("件数取得エラー")
			return 0
	
	@st.cache_data(ttl=300)  # 5分間キャッシュ
	def get_all_photos_cached(_self) -> List[Dict[str, Any]]:
		"""
		全写真データを取得（キャッシュ版）
		
		Returns:
			写真データのリスト
		"""
		# データベースのハッシュを含めてキャッシュキーを生成
		db_hash = Database._calculate_db_hash(_self.db_path)
		
		_self.connect()
		cursor = _self.conn.cursor()
		
		cursor.execute("""
			SELECT id, file_path, file_type, latitude, longitude, timestamp, created_at, location_name
			FROM photos
			ORDER BY timestamp ASC
		""")
		
		rows = cursor.fetchall()
		_self.close()
		
		# 辞書のリストに変換
		photos = []
		for row in rows:
			photos.append({
				'id': row['id'],
				'file_path': row['file_path'],
				'file_type': row['file_type'],
				'latitude': row['latitude'],
				'longitude': row['longitude'],
				'timestamp': row['timestamp'],
				'created_at': row['created_at'],
				'location_name': row['location_name'] if 'location_name' in row.keys() else None
			})
		
		return photos
	
	@st.cache_data(ttl=300)  # 5分間キャッシュ
	def count_photos_cached(_self) -> int:
		"""
		写真の総数を取得（キャッシュ版）
		
		Returns:
			写真の総数
		"""
		db_hash = Database._calculate_db_hash(_self.db_path)
		
		_self.connect()
		cursor = _self.conn.cursor()
		cursor.execute("SELECT COUNT(*) FROM photos")
		count = cursor.fetchone()[0]
		_self.close()
		
		return count

	def insert_photo(self, file_path, file_type, latitude, longitude, timestamp):
		"""
		写真データを1件登録
		
		Args:
			file_path (str): ファイルパス
			file_type (str): ファイル種類（'image' or 'video'）
			latitude (float): 緯度
			longitude (float): 経度
			timestamp (str): 撮影日時（ISO 8601形式）
			
		Returns:
			int: 登録されたレコードのID（既存の場合はNone）
		"""
		if not self.conn:
			self.connect()
		
		cursor = self.conn.cursor()
		
		try:
			cursor.execute("""
				INSERT INTO photos (file_path, file_type, latitude, longitude, timestamp)
				VALUES (?, ?, ?, ?, ?)
			""", (str(file_path), file_type, latitude, longitude, timestamp))
			
			self.conn.commit()
			self.logger.debug(f"レコード挿入: {Path(file_path).name}")
			return cursor.lastrowid
		
		except sqlite3.IntegrityError:
			# UNIQUE制約違反（既に登録済み）
			return None
		except Exception as e:
			self.logger.error(f"レコード挿入エラー: {file_path}")
			try:
				self.conn.rollback()
			except Exception:
				pass
			return None
		
		finally:
			cursor.close()
	
	def bulk_insert_from_scanner(self, scan_result, extractor_image, extractor_video):
		"""
		スキャン結果を一括登録
		
		Args:
			scan_result (dict): MediaScanner.scan_folder() の戻り値
			extractor_image: ExifExtractor クラス
			extractor_video: VideoMetadataExtractor クラス
			
		Returns:
			dict: 登録結果
				{
					'success': int,  # 成功件数
					'skipped': int,  # スキップ件数（既登録 or GPS情報なし）
					'errors': int    # エラー件数
				}
		"""
		result = {
			'success': 0,
			'skipped': 0,
			'errors': 0
		}
		
		print("\n📊 データベース登録開始...")
		print("-" * 60)
		
		# 画像を処理
		for img_path in scan_result['images']:
			try:
				metadata = extractor_image.extract_exif(img_path)
				
				# GPS情報がない場合はスキップ
				if not metadata['has_gps']:
					result['skipped'] += 1
					print(f"  ⏭️  {img_path.name} (GPS情報なし)")
					self.logger.debug(f"GPS情報なしのためスキップ: {img_path.name}")
					continue
				
				# DB登録
				row_id = self.insert_photo(
					file_path=img_path,
					file_type='image',
					latitude=metadata['latitude'],
					longitude=metadata['longitude'],
					timestamp=metadata['timestamp']
				)
				
				if row_id:
					result['success'] += 1
					print(f"  ✅ {img_path.name}")
					self.logger.debug(f"画像登録成功: {img_path.name}")
				else:
					result['skipped'] += 1
					print(f"  ⏭️  {img_path.name} (既に登録済み)")
					self.logger.debug(f"重複のためスキップ: {img_path.name}")
			
			except Exception as e:
				result['errors'] += 1
				print(f"  ❌ {img_path.name}: {str(e)}")
				self.logger.error(f"画像登録エラー: {img_path}", exc_info=False)
		
		# 動画を処理
		for vid_path in scan_result['videos']:
			try:
				metadata = extractor_video.extract_metadata(vid_path)
				
				# GPS情報がない場合はスキップ
				if not metadata['has_gps']:
					result['skipped'] += 1
					print(f"  ⏭️  {vid_path.name} (GPS情報なし)")
					self.logger.debug(f"GPS情報なしのためスキップ: {vid_path.name}")
					continue
				
				# DB登録
				row_id = self.insert_photo(
					file_path=vid_path,
					file_type='video',
					latitude=metadata['latitude'],
					longitude=metadata['longitude'],
					timestamp=metadata['timestamp']
				)
				
				if row_id:
					result['success'] += 1
					print(f"  ✅ {vid_path.name}")
					self.logger.debug(f"動画登録成功: {vid_path.name}")
				else:
					result['skipped'] += 1
					print(f"  ⏭️  {vid_path.name} (既に登録済み)")
					self.logger.debug(f"重複のためスキップ: {vid_path.name}")
			
			except Exception as e:
				result['errors'] += 1
				print(f"  ❌ {vid_path.name}: {str(e)}")
				self.logger.error(f"動画登録エラー: {vid_path}", exc_info=False)
		
		return result
	
	def get_all_photos(self):
		"""
		登録済みの全写真データを取得
		
		Returns:
			list: 写真データのリスト（辞書形式）
		"""
		try:
			if not self.conn:
				self.connect()
			
			cursor = self.conn.cursor()
			cursor.execute("""
				SELECT id, file_path, file_type, latitude, longitude, timestamp, created_at, location_name
				FROM photos
				ORDER BY timestamp ASC
			""")
			
			rows = cursor.fetchall()
			cursor.close()
			
			# 辞書形式に変換
			photos = []
			for row in rows:
				photos.append({
					'id': row['id'],
					'file_path': row['file_path'],
					'file_type': row['file_type'],
					'latitude': row['latitude'],
					'longitude': row['longitude'],
					'timestamp': row['timestamp'],
					'created_at': row['created_at'],
					'location_name': row['location_name'] if 'location_name' in row.keys() else None
				})
			
			return photos
		except Exception as e:
			self.logger.error("全データ取得エラー")
			return []
	
	def update_location_names(self, geocoder) -> int:
		"""
		location_name が空の写真に対して逆ジオコーディングを実行
		
		Args:
			geocoder: ReverseGeocoderインスタンス
			
		Returns:
			更新した件数
		"""
		try:
			self.connect()
			cursor = self.conn.cursor()
			
			# location_name が空の写真を取得
			cursor.execute("""
				SELECT id, latitude, longitude
				FROM photos
				WHERE location_name IS NULL OR location_name = ''
			""")
			
			rows = cursor.fetchall()
			
			if not rows:
				self.logger.info("更新対象の写真がありません")
				self.close()
				return 0
			
			updated = 0
			
			for row in rows:
				photo_id = row['id']
				lat = row['latitude']
				lon = row['longitude']
				
				# 逆ジオコーディング実行
				location_info = geocoder.reverse_geocode(lat, lon)
				
				if location_info:
					city = location_info.get('city') or ''
					country = location_info.get('country') or ''
					location_name = (f"{city}, {country}").strip(", ").strip()
					
					cursor.execute("""
						UPDATE photos
						SET location_name = ?
						WHERE id = ?
					""", (location_name, photo_id))
					
					updated += 1
			
			self.conn.commit()
			self.close()
			
			# キャッシュ無効化
			try:
				st.cache_data.clear()
			except Exception:
				pass
			
			self.logger.info(f"逆ジオコーディング完了: {updated}件更新")
			return updated
			
		except Exception as e:
			self.logger.error("逆ジオコーディング実行エラー")
			raise

def main():
	"""テスト実行用メイン関数"""
	print("=" * 50)
	print("JourneyMap データベース初期化テスト")
	print("=" * 50)
	
	# データベースインスタンス作成
	db = Database()
	
	# 初期化実行
	db.initialize()
	
	# テーブル情報表示
	print("\n【テーブル構造】")
	columns = db.get_table_info()
	for col in columns:
		print(f"  {col[1]:15s} {col[2]:10s}")
	
	# 件数確認
	count = db.count_photos()
	print(f"\n【登録件数】 {count} 件")
	
	# 接続クローズ
	db.close()
	
	print("\n✅ Phase 1-3 完了")
	print("=" * 50)


if __name__ == "__main__":
	main()


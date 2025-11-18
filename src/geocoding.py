"""
逆ジオコーディングモジュール
GPS座標から場所名を取得
"""

from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from typing import Optional, Dict
from pathlib import Path
import json


class ReverseGeocoder:
	"""逆ジオコーディングクラス"""
	
	def __init__(self, user_agent: str = "JourneyMap/1.0", cache_file: Path = None):
		"""
		逆ジオコーダーを初期化
		
		Args:
			user_agent: User-Agent文字列
			cache_file: キャッシュファイルのパス
		"""
		self.geocoder = Nominatim(user_agent=user_agent)
		
		# キャッシュファイル
		if cache_file is None:
			cache_file = Path("data/geocoding_cache.json")
		
		self.cache_file = cache_file
		self.cache = self._load_cache()
	
	def _load_cache(self) -> Dict[str, Dict[str, str]]:
		"""キャッシュを読み込み"""
		if self.cache_file.exists():
			try:
				with open(self.cache_file, 'r', encoding='utf-8') as f:
					return json.load(f)
			except Exception:
				return {}
		return {}
	
	def _save_cache(self):
		"""キャッシュを保存"""
		try:
			self.cache_file.parent.mkdir(parents=True, exist_ok=True)
			with open(self.cache_file, 'w', encoding='utf-8') as f:
				json.dump(self.cache, f, ensure_ascii=False, indent=2)
		except Exception as e:
			print(f"キャッシュ保存エラー: {e}")
	
	def _make_cache_key(self, latitude: float, longitude: float) -> str:
		"""キャッシュキーを生成（小数点2桁で丸める）"""
		return f"{latitude:.2f},{longitude:.2f}"
	
	def reverse_geocode(
		self,
		latitude: float,
		longitude: float,
		language: str = 'ja',
		timeout: int = 5
	) -> Optional[Dict[str, str]]:
		"""
		GPS座標から場所名を取得
		
		Args:
			latitude: 緯度
			longitude: 経度
			language: 言語（'ja', 'en'など）
			timeout: タイムアウト（秒）
			
		Returns:
			場所情報の辞書（取得失敗時はNone）
			{
				'display_name': '表示名',
				'city': '都市名',
				'country': '国名',
				'address': '住所'
			}
		"""
		# キャッシュを確認
		cache_key = self._make_cache_key(latitude, longitude)
		if cache_key in self.cache:
			return self.cache[cache_key]
		
		# APIリクエスト
		try:
			# API制限を守るため、1秒待機
			time.sleep(1)
			
			location = self.geocoder.reverse(
                f"{latitude}, {longitude}",
                language=language,
                timeout=timeout
            )
			
			if location:
				address = location.raw.get('address', {})
				
				result = {
					'display_name': location.address,
					'city': address.get('city') or address.get('town') or address.get('village') or '',
					'country': address.get('country', ''),
					'address': location.address
				}
				
				# キャッシュに保存
				self.cache[cache_key] = result
				self._save_cache()
				
				return result
			
			return None
			
		except GeocoderTimedOut:
			print(f"タイムアウト: ({latitude}, {longitude})")
			return None
		except GeocoderServiceError as e:
			print(f"ジオコーディングサービスエラー: {e}")
			return None
		except Exception as e:
			print(f"逆ジオコーディングエラー: {e}")
			return None
	
	def batch_reverse_geocode(
		self,
		coordinates: list,
		language: str = 'ja',
		max_requests: int = 100
	) -> Dict[str, Dict[str, str]]:
		"""
		複数の座標をバッチで逆ジオコーディング
		
		Args:
			coordinates: 座標のリスト [(lat, lon), ...]
			language: 言語
			max_requests: 最大リクエスト数（API制限対策）
			
		Returns:
			座標をキーとした場所情報の辞書
		"""
		results = {}
		request_count = 0
		
		for lat, lon in coordinates:
			# API制限チェック
			if request_count >= max_requests:
				print(f"APIリクエスト制限に到達（{max_requests}件）")
				break
			
			cache_key = self._make_cache_key(lat, lon)
			
			# キャッシュにある場合はスキップ
			if cache_key in self.cache:
				results[cache_key] = self.cache[cache_key]
				continue
			
			# 逆ジオコーディング実行
			location_info = self.reverse_geocode(lat, lon, language=language)
			
			if location_info:
				results[cache_key] = location_info
			
			request_count += 1
		
		return results


# テスト用コード
if __name__ == "__main__":
	geocoder = ReverseGeocoder()
	
	# テスト座標（東京タワー）
	lat, lon = 35.6586, 139.7454
	
	result = geocoder.reverse_geocode(lat, lon, language='ja')
	
	if result:
		print("逆ジオコーディング結果:")
		print(f"  表示名: {result['display_name']}")
		print(f"  都市: {result['city']}")
		print(f"  国: {result['country']}")
	else:
		print("取得失敗")



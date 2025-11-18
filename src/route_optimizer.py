"""
ルート最適化モジュール
"""

from typing import List, Dict, Any, Tuple
from itertools import permutations
import math
from src.logger import get_logger


class RouteOptimizer:
	"""ルート最適化クラス"""
	
	def __init__(self):
		self.logger = get_logger()
	
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
		# 地球の半径（km）
		R = 6371.0
		
		# ラジアンに変換
		lat1_rad = math.radians(lat1)
		lon1_rad = math.radians(lon1)
		lat2_rad = math.radians(lat2)
		lon2_rad = math.radians(lon2)
		
		# 差分
		dlat = lat2_rad - lat1_rad
		dlon = lon2_rad - lon1_rad
		
		# ハバーサイン公式
		a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
		c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
		
		distance = R * c
		return distance
	
	def build_distance_matrix(self, locations: List[Dict[str, Any]]) -> List[List[float]]:
		"""
		距離行列を構築
		
		Args:
			locations: 地点のリスト
			
		Returns:
			距離行列
		"""
		n = len(locations)
		distance_matrix = [[0.0] * n for _ in range(n)]
		
		for i in range(n):
			for j in range(n):
				if i != j:
					distance_matrix[i][j] = self.calculate_distance(
						locations[i]['latitude'],
						locations[i]['longitude'],
						locations[j]['latitude'],
						locations[j]['longitude']
					)
		
		return distance_matrix
	
	def optimize_route_exhaustive(
		self,
		locations: List[Dict[str, Any]],
		start_index: int = 0
	) -> Tuple[List[int], float]:
		"""
		全探索で最適ルートを計算（10地点以下推奨）
		
		Args:
			locations: 地点のリスト
			start_index: 開始地点のインデックス
			
		Returns:
			(最適ルート, 総距離)
		"""
		n = len(locations)
		
		if n <= 1:
			return [0], 0.0
		
		if n > 10:
			self.logger.warning(f"地点数が多い（{n}件）ため、全探索は推奨されません")
		
		# 距離行列を構築
		distance_matrix = self.build_distance_matrix(locations)
		
		# 開始地点以外のインデックス
		other_indices = [i for i in range(n) if i != start_index]
		
		best_route = None
		best_distance = float('inf')
		
		# すべての順列を試す
		for perm in permutations(other_indices):
			route = [start_index] + list(perm)
			
			# ルートの総距離を計算
			total_distance = 0.0
			for i in range(len(route) - 1):
				total_distance += distance_matrix[route[i]][route[i + 1]]
			
			# より短いルートなら更新
			if total_distance < best_distance:
				best_distance = total_distance
				best_route = route
		
		self.logger.info(f"最適ルート計算完了: {n}地点, 総距離={best_distance:.2f}km")
		return best_route, best_distance
	
	def optimize_route_greedy(
		self,
		locations: List[Dict[str, Any]],
		start_index: int = 0
	) -> Tuple[List[int], float]:
		"""
		貪欲法で近似ルートを計算（大規模データ向け）
		
		Args:
			locations: 地点のリスト
			start_index: 開始地点のインデックス
			
		Returns:
			(近似ルート, 総距離)
		"""
		n = len(locations)
		
		if n <= 1:
			return [0], 0.0
		
		# 距離行列を構築
		distance_matrix = self.build_distance_matrix(locations)
		
		# 訪問済みフラグ
		visited = [False] * n
		route = [start_index]
		visited[start_index] = True
		
		current = start_index
		total_distance = 0.0
		
		# 最も近い未訪問地点を順に訪問
		for _ in range(n - 1):
			nearest = -1
			nearest_distance = float('inf')
			
			for j in range(n):
				if not visited[j] and distance_matrix[current][j] < nearest_distance:
					nearest = j
					nearest_distance = distance_matrix[current][j]
			
			if nearest != -1:
				route.append(nearest)
				visited[nearest] = True
				total_distance += nearest_distance
				current = nearest
		
		self.logger.info(f"近似ルート計算完了: {n}地点, 総距離={total_distance:.2f}km")
		return route, total_distance
	
	def optimize_route(
		self,
		locations: List[Dict[str, Any]],
		start_index: int = 0,
		method: str = 'auto'
	) -> Tuple[List[Dict[str, Any]], float]:
		"""
		ルートを最適化
		
		Args:
			locations: 地点のリスト
			start_index: 開始地点のインデックス
			method: 'auto', 'exhaustive', 'greedy'
			
		Returns:
			(最適順序の地点リスト, 総距離)
		"""
		if not locations:
			return [], 0.0
		
		n = len(locations)
		
		# 方法を決定
		if method == 'auto':
			method = 'exhaustive' if n <= 10 else 'greedy'
		
		# ルートを計算
		if method == 'exhaustive':
			route_indices, total_distance = self.optimize_route_exhaustive(locations, start_index)
		else:
			route_indices, total_distance = self.optimize_route_greedy(locations, start_index)
		
		# インデックスから実際の地点リストに変換
		optimized_route = [locations[i] for i in route_indices]
		
		return optimized_route, total_distance
	
	def split_route_by_days(
		self,
		locations: List[Dict[str, Any]],
		days: int,
		start_index: int = 0
	) -> List[Tuple[List[Dict[str, Any]], float]]:
		"""
		複数日の旅程に分割
		
		Args:
			locations: 地点のリスト
			days: 日数
			start_index: 開始地点のインデックス
			
		Returns:
			日ごとの(地点リスト, 総距離)のリスト
		"""
		n = len(locations)
		
		if days <= 0 or n == 0:
			return []
		
		# 1日あたりの地点数を計算
		points_per_day = math.ceil(n / days)
		
		daily_routes = []
		
		for day in range(days):
			# この日の地点を抽出
			start = day * points_per_day
			end = min((day + 1) * points_per_day, n)
			
			if start >= n:
				break
			
			day_locations = locations[start:end]
			
			# この日のルートを最適化
			optimized_route, total_distance = self.optimize_route(
				day_locations,
				start_index=0 if day == 0 else 0,
				method='auto'
			)
			
			daily_routes.append((optimized_route, total_distance))
		
		self.logger.info(f"{days}日間の旅程を生成: {len(daily_routes)}日分")
		return daily_routes
	
	@staticmethod
	def estimate_travel_time(distance_km: float, speed_kmh: float = 40.0) -> float:
		"""
		移動時間を推定
		
		Args:
			distance_km: 距離（km）
			speed_kmh: 平均速度（km/h）、デフォルト40km/h（市街地）
			
		Returns:
			移動時間（時間）
		"""
		return distance_km / speed_kmh


# テスト用コード
if __name__ == "__main__":
	optimizer = RouteOptimizer()
	
	# テスト地点
	test_locations = [
		{'name': '東京タワー', 'latitude': 35.6586, 'longitude': 139.7454},
		{'name': '浅草寺', 'latitude': 35.7148, 'longitude': 139.7967},
		{'name': 'スカイツリー', 'latitude': 35.7101, 'longitude': 139.8107},
		{'name': '渋谷', 'latitude': 35.6595, 'longitude': 139.7004},
		{'name': '新宿', 'latitude': 35.6895, 'longitude': 139.6917}
	]
	
	optimized_route, total_distance = optimizer.optimize_route(test_locations)
	
	print("最適ルート:")
	for i, location in enumerate(optimized_route, 1):
		print(f"{i}. {location['name']}")
	
	print(f"\n総距離: {total_distance:.2f} km")
	print(f"推定移動時間: {optimizer.estimate_travel_time(total_distance):.1f} 時間")


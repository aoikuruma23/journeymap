"""
Folium マップ生成モジュール
インタラクティブな地図を生成し、HTMLファイルとして出力
"""

import folium
from pathlib import Path
import sys
from pathlib import Path as _PathForSysPath
# 実行方法が `python src/map_generator.py` の場合でも import できるようにパス調整
_project_root = _PathForSysPath(__file__).parent.parent
if str(_project_root) not in sys.path:
	sys.path.append(str(_project_root))

import streamlit as st
import hashlib
import json
from typing import List, Dict, Any


class MapGenerator:
    """Foliumマップ生成クラス"""
    
    def __init__(self):
        """初期化"""
        self.map = None
        self.center_lat = 35.6762  # デフォルト: 東京
        self.center_lon = 139.6503
        self.zoom_start = 10
    
    def create_base_map(self, center_lat=None, center_lon=None, zoom_start=10):
        """
        基本マップを作成
        
        Args:
            center_lat (float): 中心緯度（デフォルト: 東京）
            center_lon (float): 中心経度（デフォルト: 東京）
            zoom_start (int): 初期ズームレベル（デフォルト: 10）
            
        Returns:
            folium.Map: 作成されたマップオブジェクト
        """
        if center_lat is not None:
            self.center_lat = center_lat
        if center_lon is not None:
            self.center_lon = center_lon
        
        self.zoom_start = zoom_start
        
        # Foliumマップを作成
        self.map = folium.Map(
            location=[self.center_lat, self.center_lon],
            zoom_start=self.zoom_start,
            tiles='OpenStreetMap',  # 地図タイル
            control_scale=True      # スケールバー表示
        )
        
        print(f"✅ 基本マップを作成しました")
        print(f"   中心座標: ({self.center_lat}, {self.center_lon})")
        print(f"   ズームレベル: {self.zoom_start}")
        
        return self.map
    
    def calculate_center_from_photos(self, photos):
        """
        写真データから地図の中心座標を計算
        
        Args:
            photos (list): 写真データのリスト（辞書形式）
                各要素: {'latitude': float, 'longitude': float, ...}
        
        Returns:
            tuple: (center_lat, center_lon) または None
        """
        if not photos:
            # フォールバック（東京）
            return (self.center_lat, self.center_lon)
        
        # 緯度・経度の平均を計算
        lats = [p['latitude'] for p in photos if p['latitude'] is not None]
        lons = [p['longitude'] for p in photos if p['longitude'] is not None]
        
        if not lats or not lons:
            # フォールバック（東京）
            return (self.center_lat, self.center_lon)
        
        center_lat = sum(lats) / len(lats)
        center_lon = sum(lons) / len(lons)
        
        return center_lat, center_lon
    
    def calculate_zoom_level(self, photos):
        """
        写真データから適切なズームレベルを計算
        
        Args:
            photos (list): 写真データのリスト
            
        Returns:
            int: ズームレベル（1〜18）
        """
        if not photos or len(photos) < 2:
            return 10  # デフォルト
        
        # 緯度・経度の範囲を計算
        lats = [p['latitude'] for p in photos if p['latitude'] is not None]
        lons = [p['longitude'] for p in photos if p['longitude'] is not None]
        
        if not lats or not lons:
            return 10
        
        lat_range = max(lats) - min(lats)
        lon_range = max(lons) - min(lons)
        max_range = max(lat_range, lon_range)
        
        # 範囲に応じてズームレベルを決定（簡易ヒューリスティック）
        if max_range > 10:
            return 5
        elif max_range > 5:
            return 6
        elif max_range > 2:
            return 7
        elif max_range > 1:
            return 8
        elif max_range > 0.5:
            return 9
        elif max_range > 0.2:
            return 10
        elif max_range > 0.1:
            return 11
        elif max_range > 0.05:
            return 12
        else:
            return 13
    
    def add_route(self, photos, color='#3388ff', weight=3, opacity=0.7):
        """
        写真データから移動ルートを地図に追加
        
        Args:
            photos (list): 写真データのリスト（時系列順にソート推奨）
            color (str): ルートの色（16進数カラーコード）
            weight (int): ルートの太さ（ピクセル）
            opacity (float): ルートの不透明度（0.0〜1.0）
        
        Returns:
            int: 追加されたルートのポイント数
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。create_base_map() を先に実行してください。")
        
        valid_photos = [p for p in photos if p.get('latitude') is not None and p.get('longitude') is not None]
        if len(valid_photos) < 2:
            print("⚠️ ルートを描画するには2つ以上のGPS座標が必要です")
            return 0
        
        sorted_photos = sorted(valid_photos, key=lambda p: p.get('timestamp') or '9999-99-99')
        coordinates = [[p['latitude'], p['longitude']] for p in sorted_photos]
        
        folium.PolyLine(
            locations=coordinates,
            color=color,
            weight=weight,
            opacity=opacity,
            popup='移動ルート',
            tooltip='クリックで詳細表示'
        ).add_to(self.map)
        
        print(f"✅ ルートを描画しました（{len(coordinates)} ポイント）")
        print(f"   色: {color}, 太さ: {weight}px, 不透明度: {opacity}")
        return len(coordinates)
    
    def add_route_with_arrows(self, photos, color='#3388ff', weight=3):
        """
        矢印付きルートを描画（方向を示す）
        
        Args:
            photos (list): 写真データのリスト
            color (str): ルートの色
            weight (int): ルートの太さ
        
        Returns:
            int: ポイント数
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。")
        
        valid_photos = [p for p in photos if p.get('latitude') is not None and p.get('longitude') is not None]
        if len(valid_photos) < 2:
            return 0
        
        sorted_photos = sorted(valid_photos, key=lambda p: p.get('timestamp') or '9999-99-99')
        coordinates = [[p['latitude'], p['longitude']] for p in sorted_photos]
        
        from folium.plugins import AntPath
        AntPath(
            locations=coordinates,
            color=color,
            weight=weight,
            opacity=0.8,
            delay=800,
            dash_array=[10, 20]
        ).add_to(self.map)
        
        print(f"✅ アニメーション付きルートを描画しました（{len(coordinates)} ポイント）")
        return len(coordinates)

    @staticmethod
    def _calculate_photos_hash(photos: List[Dict[str, Any]]) -> str:
        """
        写真データのハッシュを計算
        
        Args:
            photos: 写真データのリスト
            
        Returns:
            ハッシュ値
        """
        # 写真のID、緯度、経度、時間からハッシュを生成
        hash_input = json.dumps([
            {
                'id': p.get('id'),
                'lat': p.get('latitude'),
                'lon': p.get('longitude'),
                'time': p.get('timestamp')
            }
            for p in photos
        ], sort_keys=True)
        
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    @staticmethod
    @st.cache_data(ttl=600)  # 10分間キャッシュ
    def generate_map_cached(photos: List[Dict[str, Any]], _photos_hash: str = None) -> str:
        """
        マップを生成（キャッシュ版）
        
        Args:
            photos: 写真データのリスト
            _photos_hash: 写真データのハッシュ（内部使用）
            
        Returns:
            マップのHTML文字列
        """
        # MapGeneratorインスタンスを作成
        generator = MapGenerator()
        
        # 中心座標とズームレベルを計算
        center = generator.calculate_center_from_photos(photos) or (generator.center_lat, generator.center_lon)
        zoom = generator.calculate_zoom_level(photos)
        
        # 基本マップを作成
        generator.create_base_map(
            center_lat=center[0],
            center_lon=center[1],
            zoom_start=zoom
        )
        
        # マーカーを追加
        generator.add_markers(photos)
        
        # ルートを追加
        generator.add_route(photos, color='#FF6B35', weight=4, opacity=0.8)
        
        # HTMLを取得
        return generator.map._repr_html_()
	
    def add_markers(self, photos):
        """
        写真データからマーカー（ピン）を地図に追加
        
        Args:
            photos (list): 写真データのリスト
                各要素: {
                    'id': int,
                    'file_path': str,
                    'file_type': str,
                    'latitude': float,
                    'longitude': float,
                    'timestamp': str
                }
        
        Returns:
            int: 追加されたマーカーの数
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。create_base_map() を先に実行してください。")
        
        marker_count = 0
        
        for idx, photo in enumerate(photos):
            lat = photo.get('latitude')
            lon = photo.get('longitude')
            if lat is None or lon is None:
                continue
            
            file_path = photo.get('file_path', '')
            file_name = Path(file_path).name if file_path else '不明'
            timestamp = photo.get('timestamp') or '不明'
            file_type = photo.get('file_type', 'unknown')
            
            # ファイルタイプで色・アイコンを分ける（画像=赤/カメラ、動画=青/ビデオ）
            if file_type == 'image':
                icon = folium.Icon(color='red', icon='camera', prefix='fa')
            elif file_type == 'video':
                icon = folium.Icon(color='blue', icon='video-camera', prefix='fa')
            else:
                icon = folium.Icon(color='gray', icon='question', prefix='fa')
            
            # 改善したポップアップHTML
            popup_html = f"""
            <div style="width: 220px; font-family: Arial, sans-serif;">
                <h4 style="margin: 0 0 8px 0; color: #2c5aa0;">📸 {file_name}</h4>
                <p style="margin: 4px 0; font-size: 12px;"><strong>📅 撮影日時:</strong><br>{timestamp}</p>
                <p style="margin: 4px 0; font-size: 12px;"><strong>📍 位置:</strong><br>
                   緯度: {lat:.6f}<br>
                   経度: {lon:.6f}
                </p>
                <p style="margin: 4px 0; font-size: 12px;"><strong>📁 種類:</strong> {file_type}</p>
                <hr style="margin: 8px 0;">
                <p style="margin: 0; font-size: 11px; color: #666;">
                    写真一覧パネルで詳細を確認できます
                </p>
            </div>
            """
            
            folium.Marker(
                location=[lat, lon],
                popup=folium.Popup(popup_html, max_width=260),
                tooltip=file_name,
                icon=icon
            ).add_to(self.map)
            
            marker_count += 1
        
        print(f"✅ マーカーを {marker_count} 個追加しました")
        return marker_count
    
    def add_custom_marker(self, lat, lon, label, popup_text=None, color='blue', icon='info-sign'):
        """
        カスタムマーカーを1つ追加
        
        Args:
            lat (float): 緯度
            lon (float): 経度
            label (str): ツールチップ（ホバー時の表示）
            popup_text (str): ポップアップテキスト
            color (str): マーカーの色
            icon (str): アイコン名
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。")
        
        folium.Marker(
            location=[lat, lon],
            popup=popup_text or label,
            tooltip=label,
            icon=folium.Icon(color=color, icon=icon, prefix='fa')
        ).add_to(self.map)
    
    def add_attraction_markers(
        self,
        attractions: List[Dict[str, Any]],
        show_visited: bool = True,
        show_unvisited: bool = True
    ):
        """
        観光地マーカーを追加
        
        Args:
            attractions: 観光地データのリスト
            show_visited: 訪問済み観光地を表示するか
            show_unvisited: 未訪問観光地を表示するか
        """
        if not self.map:
            raise ValueError("マップが初期化されていません")
        
        for attraction in attractions:
            visited = attraction.get('visited', False)
            
            # 表示フィルタ
            if visited and not show_visited:
                continue
            if not visited and not show_unvisited:
                continue
            
            # マーカーの色とアイコンを決定
            if visited:
                color = 'blue'
                icon = 'check'
                status_text = '✅ 訪問済み'
            else:
                color = 'green'
                icon = 'star'
                status_text = '⭐ 未訪問'
            
            # ポップアップの内容
            popup_html = f"""
                <div style="width: 200px;">
                    <h4 style="margin-bottom: 5px;">{attraction['name']}</h4>
                    <p style="margin: 3px 0;"><b>カテゴリ:</b> {attraction.get('category', '不明')}</p>
                    <p style="margin: 3px 0;"><b>場所:</b> {attraction.get('city', '')}, {attraction.get('prefecture', '')}</p>
                    <p style="margin: 3px 0;"><b>評価:</b> {'⭐' * int(attraction.get('rating', 0)) if attraction.get('rating') else 'なし'}</p>
                    <p style="margin: 3px 0;"><b>状態:</b> {status_text}</p>
            """
            
            if attraction.get('visit_date'):
                popup_html += f"""
                    <p style="margin: 3px 0;"><b>訪問日:</b> {attraction['visit_date'][:10]}</p>
                """
            
            if attraction.get('description'):
                popup_html += f"""
                    <p style="margin-top: 5px; font-size: 0.9em;">{attraction['description']}</p>
                """
            
            popup_html += """
                </div>
            """
            
            # マーカーを追加
            folium.Marker(
                location=[attraction['latitude'], attraction['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=attraction['name'],
                icon=folium.Icon(color=color, icon=icon, prefix='fa')
            ).add_to(self.map)
        
        from src.logger import get_logger
        logger = get_logger()
        logger.info(f"観光地マーカー追加: {len(attractions)}件")
    
    def add_wishlist_markers(self, wishlist_items: List[Dict[str, Any]]):
        """
        ウィッシュリストマーカーを追加
        
        Args:
            wishlist_items: ウィッシュリストアイテムのリスト
        """
        if not self.map:
            raise ValueError("マップが初期化されていません")
        
        for item in wishlist_items:
            # 優先度に応じたアイコンの色
            priority = item.get('priority', 3)
            
            # 優先度が高いほど目立つ色
            if priority >= 5:
                color = 'purple'  # 最優先
            elif priority >= 4:
                color = 'darkpurple'
            else:
                color = 'lightgray'
            
            # ポップアップの内容
            popup_html = f"""
                <div style="width: 200px;">
                    <h4 style="margin-bottom: 5px;">{'⭐' * priority} {item['name']}</h4>
                    <p style="margin: 3px 0;"><b>カテゴリ:</b> {item.get('category', '不明')}</p>
                    <p style="margin: 3px 0;"><b>場所:</b> {item.get('city', '')}, {item.get('prefecture', '')}</p>
                    <p style="margin: 3px 0;"><b>優先度:</b> {priority}/5</p>
                    <p style="margin: 3px 0;"><b>状態:</b> 📝 ウィッシュリスト</p>
            """
            
            if item.get('notes'):
                popup_html += f"""
                    <p style="margin-top: 5px; font-size: 0.9em;"><b>メモ:</b> {item['notes']}</p>
                """
            
            if item.get('planned_date'):
                popup_html += f"""
                    <p style="margin: 3px 0;"><b>予定日:</b> {item['planned_date'][:10]}</p>
                """
            
            popup_html += """
                </div>
            """
            
            # マーカーを追加
            folium.Marker(
                location=[item['latitude'], item['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=f"📝 {item['name']}",
                icon=folium.Icon(color=color, icon='heart', prefix='fa')
            ).add_to(self.map)
        
        from src.logger import get_logger
        logger = get_logger()
        logger.info(f"ウィッシュリストマーカー追加: {len(wishlist_items)}件")
    
    def add_route_preview_markers(
        self,
        route: List[Dict[str, Any]],
        color: str = '#FF6B35',
        show_numbers: bool = True
    ):
        """
        ルートプレビューマーカーを追加
        
        Args:
            route: ルートの地点リスト
            color: ルートの色
            show_numbers: 順序番号を表示するか
        """
        if not self.map:
            raise ValueError("マップが初期化されていません")
        
        # ルートラインを描画
        if len(route) >= 2:
            route_coords = [[loc['latitude'], loc['longitude']] for loc in route]
            
            folium.PolyLine(
                locations=route_coords,
                color=color,
                weight=4,
                opacity=0.8,
                popup="推奨ルート"
            ).add_to(self.map)
        
        # マーカーを追加
        for i, location in enumerate(route, 1):
            # 順序番号のアイコン
            if show_numbers:
                # 開始地点
                if i == 1:
                    icon = folium.Icon(color='green', icon='play', prefix='fa')
                    tooltip_text = f"🚩 開始: {location['name']}"
                # 終了地点
                elif i == len(route):
                    icon = folium.Icon(color='red', icon='stop', prefix='fa')
                    tooltip_text = f"🏁 終了: {location['name']}"
                # 中間地点
                else:
                    icon = folium.DivIcon(html=f"""
                        <div style="
                            background-color: {color};
                            border: 3px solid white;
                            border-radius: 50%;
                            width: 30px;
                            height: 30px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            color: white;
                            font-weight: bold;
                            font-size: 14px;
                        ">{i}</div>
                    """)
                    tooltip_text = f"{i}. {location['name']}"
            else:
                icon = folium.Icon(color='orange', icon='map-marker', prefix='fa')
                tooltip_text = location['name']
            
            # ポップアップの内容
            popup_html = f"""
                <div style="width: 200px;">
                    <h4 style="margin-bottom: 5px;">{i}. {location['name']}</h4>
                    <p style="margin: 3px 0;"><b>カテゴリ:</b> {location.get('category', '不明')}</p>
                    <p style="margin: 3px 0;"><b>場所:</b> {location.get('city', '')}, {location.get('prefecture', '')}</p>
            """
            
            if location.get('notes'):
                popup_html += f"""
                    <p style="margin-top: 5px; font-size: 0.9em;"><b>メモ:</b> {location['notes']}</p>
                """
            
            popup_html += """
                </div>
            """
            
            # マーカーを追加
            folium.Marker(
                location=[location['latitude'], location['longitude']],
                popup=folium.Popup(popup_html, max_width=250),
                tooltip=tooltip_text,
                icon=icon
            ).add_to(self.map)
        
        from src.logger import get_logger
        logger = get_logger()
        logger.info(f"ルートプレビューマーカー追加: {len(route)}地点")
    
    def save_map(self, output_path='output/map.html'):
        """
        マップをHTMLファイルとして保存
        
        Args:
            output_path (str): 出力ファイルパス
            
        Returns:
            Path: 保存されたファイルのパス
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。create_base_map() を先に実行してください。")
        
        # 出力ディレクトリを作成
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # HTML保存
        self.map.save(str(output_path))
        
        print(f"✅ マップを保存しました: {output_path}")
        
        return output_path
    
    def get_map_html(self):
        """
        マップのHTML文字列を取得
        
        Returns:
            str: マップのHTML
        """
        if self.map is None:
            raise ValueError("マップが作成されていません。")
        
        return self.map._repr_html_()


def main():
	"""テスト実行用メイン関数"""
	print("=" * 60)
	print("Folium マップ生成モジュール テスト（Phase 3-3）")
	print("=" * 60)
	
	# データベースから写真データを取得
	from src.database import Database
	
	db = Database()
	db.initialize()
	
	photos = db.get_all_photos()
	
	if not photos:
		print("\n⚠️ データベースに写真データがありません")
		print("   代わりにサンプルデータでテストを実行します...")
		
		photos = [
			{
				'id': 1, 'file_path': 'sample/tokyo_station.jpg', 'file_type': 'image',
				'latitude': 35.6812, 'longitude': 139.7671, 'timestamp': '2024-03-15T09:00:00'
			},
			{
				'id': 2, 'file_path': 'sample/imperial_palace.jpg', 'file_type': 'image',
				'latitude': 35.6852, 'longitude': 139.7528, 'timestamp': '2024-03-15T10:30:00'
			},
			{
				'id': 3, 'file_path': 'sample/shibuya.jpg', 'file_type': 'image',
				'latitude': 35.6595, 'longitude': 139.7004, 'timestamp': '2024-03-15T14:00:00'
			},
			{
				'id': 4, 'file_path': 'sample/skytree.mp4', 'file_type': 'video',
				'latitude': 35.7101, 'longitude': 139.8107, 'timestamp': '2024-03-15T16:30:00'
			},
			{
				'id': 5, 'file_path': 'sample/odaiba.jpg', 'file_type': 'image',
				'latitude': 35.6249, 'longitude': 139.7751, 'timestamp': '2024-03-15T18:00:00'
			}
		]
	
	db.close()
	
	print(f"\n📊 使用する写真データ: {len(photos)} 件")
	
	# マップジェネレータを作成
	generator = MapGenerator()
	
	# 中心座標とズームレベルを自動計算
	center = generator.calculate_center_from_photos(photos)
	zoom = generator.calculate_zoom_level(photos)
	
	print(f"   中心座標: {center}")
	print(f"   ズームレベル: {zoom}")
	
	# マップを作成
	print("\n【ステップ1】基本マップ作成")
	generator.create_base_map(center_lat=center[0], center_lon=center[1], zoom_start=zoom)
	
	# マーカーを追加
	print("\n【ステップ2】マーカー追加")
	marker_count = generator.add_markers(photos)
	
	# ルートを追加
	print("\n【ステップ3】ルート描画")
	route_points = generator.add_route(photos, color='#FF5733', weight=4, opacity=0.8)
	
	# 保存
	print("\n【ステップ4】HTML保存")
	output_path = generator.save_map('output/map_with_route.html')
	
	# アニメーション付きルートのテスト
	print("\n" + "-" * 60)
	print("【追加テスト】アニメーション付きルート")
	generator2 = MapGenerator()
	generator2.create_base_map(center_lat=center[0], center_lon=center[1], zoom_start=zoom)
	generator2.add_markers(photos)
	generator2.add_route_with_arrows(photos, color='#3388ff', weight=4)
	output_path2 = generator2.save_map('output/map_with_animated_route.html')
	
	print("\n" + "=" * 60)
	print("✅ Phase 3-3 テスト完了")
	print("=" * 60)
	print(f"\n📁 生成されたファイル:")
	print(f"  1. {output_path}")
	print(f"  2. {output_path2}")
	print(f"\n🌐 ブラウザで開いて確認してください:")
	print(f"   file:///{output_path.absolute()}")
	print("\n【確認ポイント】")
	print(f"  ✅ {marker_count} 個のマーカーが表示される")
	print(f"  ✅ {route_points} ポイントを結ぶルートが描画される")
	print("  ✅ ルートが時系列順に描画される")
	print("  ✅ アニメーション版ではルートが動く")


if __name__ == "__main__":
    main()


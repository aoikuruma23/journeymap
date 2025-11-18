"""
Phase 3 統合テスト: マップ生成エンジン
データベース → マップ生成（マーカー + ルート）→ HTML出力
"""

from pathlib import Path
from src.database import Database
from src.map_generator import MapGenerator


def main():
	print("=" * 70)
	print("Phase 3 統合テスト: マップ生成エンジン")
	print("=" * 70)
	
	# ステップ1: データベースから写真データを取得
	print("\n【ステップ1】データベースから写真データを取得")
	db = Database()
	db.initialize()
	
	photos = db.get_all_photos()
	
	if not photos:
		print("⚠️ データベースに写真データがありません")
		print("   サンプルデータを使用します...")
		
		# サンプルデータ（日本の主要都市ツアー）
		photos = [
			{
				'id': 1, 'file_path': 'sample/tokyo.jpg', 'file_type': 'image',
				'latitude': 35.6812, 'longitude': 139.7671, 'timestamp': '2024-03-01T09:00:00'
			},
			{
				'id': 2, 'file_path': 'sample/yokohama.jpg', 'file_type': 'image',
				'latitude': 35.4437, 'longitude': 139.6380, 'timestamp': '2024-03-01T12:00:00'
			},
			{
				'id': 3, 'file_path': 'sample/hakone.mp4', 'file_type': 'video',
				'latitude': 35.2322, 'longitude': 139.1069, 'timestamp': '2024-03-01T15:00:00'
			},
			{
				'id': 4, 'file_path': 'sample/fuji.jpg', 'file_type': 'image',
				'latitude': 35.3606, 'longitude': 138.7274, 'timestamp': '2024-03-01T18:00:00'
			},
			{
				'id': 5, 'file_path': 'sample/shizuoka.jpg', 'file_type': 'image',
				'latitude': 34.9756, 'longitude': 138.3828, 'timestamp': '2024-03-02T10:00:00'
			},
			{
				'id': 6, 'file_path': 'sample/nagoya.jpg', 'file_type': 'image',
				'latitude': 35.1815, 'longitude': 136.9066, 'timestamp': '2024-03-02T14:00:00'
			},
			{
				'id': 7, 'file_path': 'sample/kyoto.jpg', 'file_type': 'image',
				'latitude': 35.0116, 'longitude': 135.7681, 'timestamp': '2024-03-03T09:00:00'
			},
			{
				'id': 8, 'file_path': 'sample/osaka.mp4', 'file_type': 'video',
				'latitude': 34.6937, 'longitude': 135.5023, 'timestamp': '2024-03-03T15:00:00'
			}
		]
	
	db.close()
	
	print(f"✅ 写真データを {len(photos)} 件取得しました")
	
	# 画像と動画の内訳
	images = [p for p in photos if p['file_type'] == 'image']
	videos = [p for p in photos if p['file_type'] == 'video']
	print(f"   ├─ 画像: {len(images)} 件")
	print(f"   └─ 動画: {len(videos)} 件")
	
	# ステップ2: マップジェネレータを作成
	print("\n【ステップ2】マップジェネレータを作成")
	generator = MapGenerator()
	
	# 中心座標とズームレベルを自動計算
	center = generator.calculate_center_from_photos(photos)
	zoom = generator.calculate_zoom_level(photos)
	
	print(f"✅ 中心座標を計算: {center}")
	print(f"✅ ズームレベルを計算: {zoom}")
	
	# ステップ3: 基本マップを作成
	print("\n【ステップ3】基本マップを作成")
	generator.create_base_map(center_lat=center[0], center_lon=center[1], zoom_start=zoom)
	
	# ステップ4: マーカーを追加
	print("\n【ステップ4】マーカー（ピン）を追加")
	marker_count = generator.add_markers(photos)
	
	# ステップ5: ルートを描画
	print("\n【ステップ5】移動ルートを描画")
	route_points = generator.add_route(photos, color='#FF6B35', weight=4, opacity=0.8)
	
	# ステップ6: HTMLファイルとして保存
	print("\n【ステップ6】HTMLファイルとして保存")
	output_path = generator.save_map('output/journey_map.html')
	
	# 結果サマリー
	print("\n" + "=" * 70)
	print("【生成結果サマリー】")
	print("=" * 70)
	print(f"📊 データ:")
	print(f"   ├─ 写真データ: {len(photos)} 件")
	print(f"   ├─ マーカー: {marker_count} 個")
	print(f"   └─ ルートポイント: {route_points} 個")
	print(f"\n📁 出力ファイル:")
	print(f"   {output_path}")
	print(f"\n📏 ファイルサイズ:")
	print(f"   {output_path.stat().st_size / 1024:.2f} KB")
	print(f"\n🌐 ブラウザで確認:")
	print(f"   file:///{output_path.absolute()}")
	
	# 検証項目
	print("\n" + "=" * 70)
	print("【検証チェックリスト】")
	print("=" * 70)
	print("ブラウザで以下を確認してください：")
	print(f"  ✅ マーカー（ピン）が {marker_count} 個表示される")
	print(f"  ✅ 画像は青いピン、動画は赤いピンで表示される")
	print(f"  ✅ マーカーをクリックするとポップアップが表示される")
	print(f"  ✅ マーカーにホバーするとファイル名が表示される")
	print(f"  ✅ {route_points} ポイントを結ぶルート（線）が表示される")
	print("  ✅ ルートが時系列順に描画されている")
	print("  ✅ ドラッグで地図を移動できる")
	print("  ✅ スクロールでズームイン/アウトできる")
	
	print("\n" + "=" * 70)
	print("✅ Phase 3（マップ生成エンジン）完了")
	print("=" * 70)
	print("\n次のステップ: Phase 4（Streamlit UI統合）")


if __name__ == "__main__":
	main()


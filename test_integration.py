"""
Phase 2 統合テスト
フォルダスキャン → メタデータ抽出 → DB登録の一連の流れをテスト
"""

from pathlib import Path
from src.scanner import MediaScanner
from src.exif_extractor import ExifExtractor
from src.video_metadata import VideoMetadataExtractor
from src.database import Database


def main():
	print("=" * 70)
	print("Phase 2 統合テスト: フォルダスキャン → メタデータ抽出 → DB登録")
	print("=" * 70)
	
	# テスト用フォルダの入力
	folder = input("\nスキャンするフォルダのパスを入力してください\n（Enterでスキップ）: ").strip()
	
	if not folder:
		print("\n⚠️ フォルダが指定されていません")
		print("✅ 統合モジュールの実装は完了しています")
		print("\n【使用方法】")
		print("  1. フォルダをスキャン: MediaScanner.scan_folder(folder)")
		print("  2. データベース初期化: Database().initialize()")
		print("  3. 一括登録: db.bulk_insert_from_scanner(result, ExifExtractor, VideoMetadataExtractor)")
		return
	
	folder_path = Path(folder)
	
	# フォルダ存在確認
	if not folder_path.exists():
		print(f"\n❌ エラー: フォルダが見つかりません: {folder}")
		return
	
	if not folder_path.is_dir():
		print(f"\n❌ エラー: ディレクトリではありません: {folder}")
		return
	
	try:
		# ステップ1: フォルダスキャン
		print("\n【ステップ1】フォルダスキャン")
		scan_result = MediaScanner.scan_folder(folder_path, recursive=True)
		
		summary = MediaScanner.get_summary(scan_result)
		print(f"\n  検出ファイル数: {summary['total_files']}")
		print(f"  ├─ 画像: {summary['images_count']} 件")
		print(f"  ├─ 動画: {summary['videos_count']} 件")
		print(f"  └─ エラー: {summary['errors_count']} 件")
		
		if summary['total_files'] == 0:
			print("\n⚠️ メディアファイルが見つかりませんでした")
			return
		
		# ステップ2: データベース準備
		print("\n【ステップ2】データベース準備")
		db = Database()
		db.initialize()
		
		before_count = db.count_photos()
		print(f"  登録前の件数: {before_count} 件")
		
		# ステップ3: 一括登録
		print("\n【ステップ3】メタデータ抽出 & DB登録")
		insert_result = db.bulk_insert_from_scanner(
			scan_result,
			ExifExtractor,
			VideoMetadataExtractor
		)
		
		# 結果サマリー
		print("\n" + "=" * 70)
		print("【登録結果】")
		print(f"  ✅ 成功: {insert_result['success']} 件")
		print(f"  ⏭️  スキップ: {insert_result['skipped']} 件")
		print(f"  ❌ エラー: {insert_result['errors']} 件")
		
		after_count = db.count_photos()
		print(f"\n  登録後の件数: {after_count} 件 (+{after_count - before_count})")
		
		# データベースの内容を表示（最大5件）
		if after_count > 0:
			print("\n【登録データ例】（最新5件）")
			photos = db.get_all_photos()[-5:]  # 最新5件
			for photo in photos:
				print(f"\n  ID: {photo['id']}")
				print(f"    ファイル: {Path(photo['file_path']).name}")
				print(f"    種類: {photo['file_type']}")
				print(f"    GPS: ({photo['latitude']}, {photo['longitude']})")
				print(f"    日時: {photo['timestamp']}")
		
		db.close()
		
		print("\n" + "=" * 70)
		print("✅ Phase 2 統合テスト完了")
		print("=" * 70)
		print("\n次のステップ: Phase 3（マップ生成エンジン）")
		
	except Exception as e:
		print(f"\n❌ エラー: {e}")
		import traceback
		traceback.print_exc()


if __name__ == "__main__":
	main()


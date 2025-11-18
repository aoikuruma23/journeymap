"""
フォルダスキャンモジュール
指定フォルダを再帰的に探索し、写真・動画ファイルを検出
"""

import sys
from pathlib import Path as _PathForSysPath
# 実行方法が `python src/scanner.py` の場合でも import できるようにパス調整
_project_root = _PathForSysPath(__file__).parent.parent
if str(_project_root) not in sys.path:
	sys.path.append(str(_project_root))

from pathlib import Path
from src.exif_extractor import ExifExtractor
from src.video_metadata import VideoMetadataExtractor


class MediaScanner:
    """メディアファイルスキャナークラス"""
    
    @staticmethod
    def scan_folder(folder_path, recursive=True):
        """
        フォルダをスキャンして写真・動画ファイルを検出
        
        Args:
            folder_path (str or Path): スキャンするフォルダのパス
            recursive (bool): サブフォルダも探索するか（デフォルト: True）
            
        Returns:
            dict: スキャン結果
                {
                    'images': [Path, Path, ...],
                    'videos': [Path, Path, ...],
                    'total': int,
                    'errors': [str, str, ...]
                }
        """
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"フォルダが見つかりません: {folder_path}")
        
        if not folder_path.is_dir():
            raise ValueError(f"ディレクトリではありません: {folder_path}")
        
        # 結果の初期化
        result = {
            'images': [],
            'videos': [],
            'total': 0,
            'errors': []
        }
        
        print(f"📂 スキャン開始: {folder_path}")
        print(f"   再帰探索: {'ON' if recursive else 'OFF'}")
        print("-" * 60)
        
        try:
            # ファイルを探索
            if recursive:
                # 再帰的に探索（サブフォルダ含む）
                files = folder_path.rglob('*')
            else:
                # 指定フォルダのみ
                files = folder_path.glob('*')
            
            # ファイルを分類
            for file_path in files:
                if not file_path.is_file():
                    continue
                
                try:
                    # 写真ファイルかチェック
                    if ExifExtractor.is_supported(file_path):
                        result['images'].append(file_path)
                        print(f"  📷 画像: {file_path.name}")
                    
                    # 動画ファイルかチェック
                    elif VideoMetadataExtractor.is_supported(file_path):
                        result['videos'].append(file_path)
                        print(f"  🎬 動画: {file_path.name}")
                
                except Exception as e:
                    error_msg = f"エラー ({file_path.name}): {str(e)}"
                    result['errors'].append(error_msg)
                    print(f"  ⚠️ {error_msg}")
            
            # 合計数を計算
            result['total'] = len(result['images']) + len(result['videos'])
            
        except Exception as e:
            raise RuntimeError(f"スキャン中にエラーが発生しました: {e}")
        
        return result
    
    @staticmethod
    def get_summary(scan_result):
        """
        スキャン結果のサマリーを取得
        
        Args:
            scan_result (dict): scan_folder() の戻り値
            
        Returns:
            dict: サマリー情報
        """
        return {
            'total_files': scan_result['total'],
            'images_count': len(scan_result['images']),
            'videos_count': len(scan_result['videos']),
            'errors_count': len(scan_result['errors'])
        }
    
    @staticmethod
    def filter_with_gps(files, file_type='image'):
        """
        GPS情報を持つファイルのみをフィルタリング
        
        Args:
            files (list): ファイルパスのリスト
            file_type (str): 'image' または 'video'
            
        Returns:
            list: GPS情報を持つファイルのリスト
        """
        gps_files = []
        
        print(f"\n🌍 GPS情報チェック（{file_type}）...")
        
        for file_path in files:
            try:
                if file_type == 'image':
                    metadata = ExifExtractor.extract_exif(file_path)
                else:
                    metadata = VideoMetadataExtractor.extract_metadata(file_path)
                
                if metadata.get('has_gps', False):
                    gps_files.append(file_path)
                    print(f"  ✅ {file_path.name}")
                else:
                    print(f"  ❌ {file_path.name} (GPS情報なし)")
            
            except Exception as e:
                print(f"  ⚠️ {file_path.name}: エラー ({e})")
        
        return gps_files


def main():
    """テスト実行用メイン関数"""
    print("=" * 60)
    print("フォルダスキャンモジュール テスト")
    print("=" * 60)
    
    # テスト用：フォルダパスを入力
    folder = input("\nスキャンするフォルダのパスを入力してください\n（Enterでスキップ）: ").strip()
    
    if not folder:
        print("\n⚠️ フォルダが指定されていません")
        print("✅ モジュールの実装は完了しています")
        print("\n【使用方法】")
        print("  from src.scanner import MediaScanner")
        print("  result = MediaScanner.scan_folder('path/to/folder')")
        print("  print(result)")
        return
    
    folder_path = Path(folder)
    
    # フォルダ存在確認
    if not folder_path.exists():
        print(f"\n❌ エラー: フォルダが見つかりません: {folder}")
        return
    
    if not folder_path.is_dir():
        print(f"\n❌ エラー: ディレクトリではありません: {folder}")
        return
    
    # スキャン実行
    try:
        result = MediaScanner.scan_folder(folder_path, recursive=True)
        
        # サマリー表示
        print("\n" + "=" * 60)
        print("【スキャン結果】")
        summary = MediaScanner.get_summary(result)
        print(f"  合計ファイル数: {summary['total_files']}")
        print(f"  ├─ 画像: {summary['images_count']} 件")
        print(f"  ├─ 動画: {summary['videos_count']} 件")
        print(f"  └─ エラー: {summary['errors_count']} 件")
        
        # GPS情報チェック（オプション）
        if result['images']:
            check_gps = input("\nGPS情報をチェックしますか？ (y/n): ").strip().lower()
            if check_gps == 'y':
                gps_images = MediaScanner.filter_with_gps(result['images'], 'image')
                print(f"\n✅ GPS情報を持つ画像: {len(gps_images)} / {len(result['images'])} 件")
        
        print("\n" + "=" * 60)
        print("✅ Phase 2-3 テスト完了")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")


if __name__ == "__main__":
    main()


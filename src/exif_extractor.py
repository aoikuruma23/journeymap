"""
写真EXIF情報抽出モジュール
JPG, PNG, HEIC からGPS座標と撮影日時を抽出
"""

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any
from src.logger import get_logger


class ExifExtractor:
    """EXIF情報抽出クラス"""

    SUPPORTED_FORMATS = ['.jpg', '.jpeg', '.png', '.heic']

    @staticmethod
    def is_supported(file_path):
        """
        対応フォーマットかどうかを判定
        
        Args:
            file_path (str or Path): ファイルパス
            
        Returns:
            bool: 対応フォーマットならTrue
        """
        ext = Path(file_path).suffix.lower()
        return ext in ExifExtractor.SUPPORTED_FORMATS

    @staticmethod
    def extract_exif(file_path) -> Dict[str, Any]:
        """
        EXIF情報を抽出
        
        Args:
            file_path (str or Path): 画像ファイルのパス
            
        Returns:
            dict: 抽出されたEXIF情報
                {
                    'latitude': float or None,
                    'longitude': float or None,
                    'timestamp': str or None,  # ISO 8601形式
                    'has_gps': bool
                }
        """
        logger = get_logger()
        file_path = Path(file_path)
        
        if not file_path.exists():
            logger.warning(f"EXIF抽出: ファイルが見つかりません: {file_path}")
            # 呼び出し側互換のため空の結果を返す
            return {
                'latitude': None, 'longitude': None, 'timestamp': None, 'has_gps': False
            }
        
        if not ExifExtractor.is_supported(file_path):
            logger.warning(f"EXIF抽出: 非対応フォーマット: {file_path.suffix}")
            return {
                'latitude': None, 'longitude': None, 'timestamp': None, 'has_gps': False
            }
        
        # 結果の初期化
        result = {
            'latitude': None,
            'longitude': None,
            'timestamp': None,
            'has_gps': False
        }
        
        try:
            logger.debug(f"EXIF抽出開始: {file_path}")
            # 大容量ファイルの事前警告
            try:
                size = file_path.stat().st_size
                if size > 100 * 1024 * 1024:
                    logger.warning(f"EXIF抽出: ファイルサイズが大きい（{size / 1024 / 1024:.1f}MB）: {file_path}")
            except Exception:
                pass
            # Pillowでの抽出を試みる
            result = ExifExtractor._extract_with_pillow(file_path, result)
            
            # GPS情報がない場合、exifreadで再試行
            if not result['has_gps']:
                result = ExifExtractor._extract_with_exifread(file_path, result)
            
        except Exception as e:
            logger.error(f"EXIF抽出で予期しないエラー: {file_path.name}", exc_info=True)
        
        return result

    @staticmethod
    def _extract_with_pillow(file_path, result):
        """Pillowを使用してEXIF抽出"""
        try:
            with Image.open(file_path) as img:
                exif_data = getattr(img, "_getexif", lambda: None)()
                
                if not exif_data:
                    return result
                
                # GPS情報の抽出
                gps_info = exif_data.get(34853)  # GPSInfo タグ
                if gps_info:
                    lat, lon = ExifExtractor._parse_gps(gps_info)
                    if lat is not None and lon is not None:
                        result['latitude'] = lat
                        result['longitude'] = lon
                        result['has_gps'] = True
                
                # 撮影日時の抽出
                datetime_original = exif_data.get(36867)  # DateTimeOriginal
                if datetime_original:
                    result['timestamp'] = ExifExtractor._parse_datetime(datetime_original)
                
        except Exception:
            # Pillow で失敗しても続行（exifreadで再試行）
            pass
        
        return result

    @staticmethod
    def _extract_with_exifread(file_path, result):
        """exifreadを使用してEXIF抽出（フォールバック）"""
        try:
            with open(file_path, 'rb') as f:
                tags = exifread.process_file(f)
                
                # GPS情報
                if 'GPS GPSLatitude' in tags and 'GPS GPSLongitude' in tags:
                    lat = ExifExtractor._convert_to_degrees(tags['GPS GPSLatitude'])
                    lon = ExifExtractor._convert_to_degrees(tags['GPS GPSLongitude'])
                    
                    # 南緯・西経の処理
                    if 'GPS GPSLatitudeRef' in tags and getattr(tags['GPS GPSLatitudeRef'], "values", "") == 'S':
                        lat = -lat
                    if 'GPS GPSLongitudeRef' in tags and getattr(tags['GPS GPSLongitudeRef'], "values", "") == 'W':
                        lon = -lon
                    
                    result['latitude'] = lat
                    result['longitude'] = lon
                    result['has_gps'] = True
                
                # 撮影日時
                if 'EXIF DateTimeOriginal' in tags:
                    result['timestamp'] = ExifExtractor._parse_datetime(str(tags['EXIF DateTimeOriginal']))
                
        except Exception:
            pass
        
        return result

    @staticmethod
    def _parse_gps(gps_info):
        """
        GPS情報を10進数の座標に変換
        
        Args:
            gps_info (dict): GPSInfo辞書
            
        Returns:
            tuple: (latitude, longitude) or (None, None)
        """
        try:
            lat = gps_info.get(2)  # GPSLatitude
            lon = gps_info.get(4)  # GPSLongitude
            lat_ref = gps_info.get(1)  # GPSLatitudeRef (N/S)
            lon_ref = gps_info.get(3)  # GPSLongitudeRef (E/W)

            if lat and lon:
                # 度分秒 → 10進数変換（各要素は IFDRational / tuple / exifread のRational 等の可能性）
                def rational_to_float(v):
                    try:
                        # PIL.IFDRational: numerator/denominator
                        if hasattr(v, "numerator") and hasattr(v, "denominator"):
                            return float(v.numerator) / float(v.denominator)
                        # exifread Ratio: num/den
                        if hasattr(v, "num") and hasattr(v, "den"):
                            return float(v.num) / float(v.den)
                        # 既に float/int の場合
                        return float(v)
                    except Exception:
                        return float(v)

                def to_float(x):
                    d = rational_to_float(x[0])
                    m = rational_to_float(x[1])
                    s = rational_to_float(x[2])
                    return d + (m / 60.0) + (s / 3600.0)

                lat_deg = to_float(lat)
                lon_deg = to_float(lon)

                # 参照（N/S/E/W）は bytes のことがあるので大文字化して判定
                def normalize_ref(ref):
                    try:
                        if isinstance(ref, bytes):
                            ref = ref.decode(errors="ignore")
                        ref = str(ref).strip().upper()
                        return ref[:1] if ref else ""
                    except Exception:
                        return ""

                lat_ref_n = normalize_ref(lat_ref)
                lon_ref_n = normalize_ref(lon_ref)

                # 南緯・西経の処理
                if lat_ref_n == 'S':
                    lat_deg = -lat_deg
                if lon_ref_n == 'W':
                    lon_deg = -lon_deg

                return lat_deg, lon_deg
        except Exception:
            pass

        return None, None

    @staticmethod
    def _convert_to_degrees(value):
        """
        exifread形式のGPS座標を10進数に変換
        
        Args:
            value: exifreadのGPS座標値
            
        Returns:
            float: 10進数座標
        """
        d = float(value.values[0].num) / float(value.values[0].den)
        m = float(value.values[1].num) / float(value.values[1].den)
        s = float(value.values[2].num) / float(value.values[2].den)
        
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def _parse_datetime(dt_str):
        """
        EXIF日時文字列をISO 8601形式に変換
        
        Args:
            dt_str (str): EXIF日時文字列（例: "2024:03:15 14:30:45"）
            
        Returns:
            str: ISO 8601形式（例: "2024-03-15T14:30:45"）
        """
        try:
            # EXIF形式: "YYYY:MM:DD HH:MM:SS"
            dt = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")
            return dt.isoformat()
        except Exception:
            return None


def main():
    """テスト実行用メイン関数"""
    print("=" * 60)
    print("EXIF抽出モジュール テスト")
    print("=" * 60)
    
    # テスト用：実際の画像ファイルパスを指定してテスト
    test_file = input("\nテスト用画像ファイルのパスを入力してください\n（Enterでスキップ）: ").strip()
    
    if not test_file:
        print("\n⚠️ テストファイルが指定されていません")
        print("✅ モジュールの実装は完了しています")
        print("\n【使用方法】")
        print("  from src.exif_extractor import ExifExtractor")
        print("  result = ExifExtractor.extract_exif('path/to/photo.jpg')")
        print("  print(result)")
        return
    
    # ファイル存在確認
    if not Path(test_file).exists():
        print(f"\n❌ エラー: ファイルが見つかりません: {test_file}")
        return
    
    # 対応フォーマット確認
    if not ExifExtractor.is_supported(test_file):
        print(f"\n❌ エラー: 非対応フォーマット: {Path(test_file).suffix}")
        return
    
    print(f"\n📷 テストファイル: {Path(test_file).name}")
    print("-" * 60)
    
    # EXIF抽出実行
    result = ExifExtractor.extract_exif(test_file)
    
    # 結果表示
    print("\n【抽出結果】")
    print(f"  GPS座標:")
    if result['has_gps']:
        print(f"    ✅ 緯度: {result['latitude']}")
        print(f"    ✅ 経度: {result['longitude']}")
    else:
        print(f"    ❌ GPS情報なし")
    
    print(f"\n  撮影日時:")
    if result['timestamp']:
        print(f"    ✅ {result['timestamp']}")
    else:
        print(f"    ❌ 日時情報なし")
    
    print("\n" + "=" * 60)
    print("✅ Phase 2-1 テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    main()


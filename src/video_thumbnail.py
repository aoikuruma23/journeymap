"""
動画サムネイル生成モジュール
"""

import cv2
from pathlib import Path
from PIL import Image
import tempfile
from typing import Optional
from src.logger import get_logger


class VideoThumbnailGenerator:
	"""動画からサムネイル画像を生成するクラス"""
	
	@staticmethod
	def generate_thumbnail(
		video_path: Path,
		output_dir: Optional[Path] = None,
		frame_position: float = 0.1,
		max_size: tuple = (300, 300)
	) -> Optional[Path]:
		"""
		動画からサムネイル画像を生成
		
		Args:
			video_path: 動画ファイルのパス
			output_dir: サムネイル保存先（Noneの場合は一時ディレクトリ）
			frame_position: 抽出するフレームの位置（0.0〜1.0）
			max_size: サムネイルの最大サイズ (width, height)
			
		Returns:
			サムネイル画像のパス（失敗時はNone）
		"""
		try:
			logger = get_logger()
			logger.debug(f"サムネイル生成開始: {video_path}")
			# 動画ファイルを開く
			video = cv2.VideoCapture(str(video_path))
			
			if not video.isOpened():
				logger.warning(f"動画を開けません: {video_path}")
				return None
			
			# 総フレーム数を取得
			total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT))
			
			if total_frames == 0:
				video.release()
				logger.warning(f"フレーム数が0です: {video_path}")
				return None
			
			# 抽出するフレーム位置を計算
			target_frame = int(total_frames * frame_position)
			
			# 指定フレームまでシーク
			video.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
			
			# フレームを読み込み
			success, frame = video.read()
			video.release()
			
			if not success:
				logger.warning(f"フレーム取得に失敗: {video_path} pos={target_frame}")
				return None
			
			# BGRからRGBに変換
			frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			
			# PIL Imageに変換
			img = Image.fromarray(frame_rgb)
			
			# サムネイルサイズにリサイズ（アスペクト比維持）
			img.thumbnail(max_size, Image.Resampling.LANCZOS)
			
			# 保存先を決定
			if output_dir is None:
				output_dir = Path(tempfile.gettempdir()) / "journeymap_thumbnails"
			
			output_dir.mkdir(parents=True, exist_ok=True)
			
			# サムネイルファイル名を生成
			thumbnail_name = f"{video_path.stem}_thumb.jpg"
			thumbnail_path = output_dir / thumbnail_name
			
			# サムネイルを保存
			img.save(thumbnail_path, "JPEG", quality=85)
			
			logger.info(f"サムネイル生成成功: {thumbnail_path.name}")
			return thumbnail_path
			
		except Exception as e:
			logger.error(f"サムネイル生成エラー: {video_path}", exc_info=True)
			return None
	
	@staticmethod
	def get_video_info(video_path: Path) -> dict:
		"""
		動画の情報を取得
		
		Args:
			video_path: 動画ファイルのパス
			
		Returns:
			動画情報の辞書
		"""
		try:
			logger = get_logger()
			logger.debug(f"動画情報取得: {video_path}")
			video = cv2.VideoCapture(str(video_path))
			
			if not video.isOpened():
				logger.warning(f"動画を開けません: {video_path}")
				return {}
			
			fps = video.get(cv2.CAP_PROP_FPS) or 0.0
			total_frames = int(video.get(cv2.CAP_PROP_FRAME_COUNT)) or 0
			duration = (total_frames / fps) if fps > 0 else 0.0
			
			info = {
				'duration': duration,
				'fps': fps,
				'width': int(video.get(cv2.CAP_PROP_FRAME_WIDTH)) or 0,
				'height': int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 0,
				'total_frames': total_frames
			}
			
			video.release()
			logger.debug(f"動画情報: duration={info['duration']:.2f}s fps={info['fps']:.2f} size={info['width']}x{info['height']} frames={info['total_frames']}")
			return info
			
		except Exception as e:
			logger.error(f"動画情報取得エラー: {video_path}", exc_info=True)
			return {}

# テスト用コード
if __name__ == "__main__":
	# テスト実行例
	import sys
	
	if len(sys.argv) > 1:
		video_path = Path(sys.argv[1])
		
		if video_path.exists():
			print(f"動画ファイル: {video_path}")
			
			# サムネイル生成
			thumbnail = VideoThumbnailGenerator.generate_thumbnail(video_path)
			
			if thumbnail:
				print(f"✅ サムネイル生成成功: {thumbnail}")
			else:
				print("❌ サムネイル生成失敗")
			
			# 動画情報取得
			info = VideoThumbnailGenerator.get_video_info(video_path)
			print(f"動画情報: {info}")
		else:
			print(f"❌ ファイルが見つかりません: {video_path}")
	else:
		print("使用方法: python video_thumbnail.py <動画ファイルパス>")


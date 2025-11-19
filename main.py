"""
JourneyMap - メインアプリケーション
Streamlit を使用した写真マップアプリ
"""

import streamlit as st
from pathlib import Path
from src.scanner import MediaScanner
from src.exif_extractor import ExifExtractor
from src.video_metadata import VideoMetadataExtractor
from src.database import Database
from io import BytesIO
from PIL import Image, ImageOps

# 画像読み込み＆リサイズ（キャッシュ）
@st.cache_data(ttl=3600)
def load_resized_image_bytes(file_path: str, long_edge: int, quality: int, mtime: float) -> bytes:
	"""
	指定された長辺ピクセルに収まるようにリサイズしたJPEGバイト列を返す。
	キャッシュキーにファイルの更新時刻（mtime）も含める。
	"""
	p = Path(file_path)
	with Image.open(p) as img:
		# EXIFの回転を適用して正しい向きに
		img = ImageOps.exif_transpose(img)
		img = img.convert("RGB")
		
		if long_edge > 0:
			w, h = img.size
			scale = long_edge / max(w, h)
			new_size = (int(w * scale), int(h * scale))
			if max(new_size) < max(w, h):
				img = img.resize(new_size, Image.LANCZOS)
		
		buf = BytesIO()
		img.save(buf, format="JPEG", quality=quality, optimize=True)
		return buf.getvalue()


def main():
	"""メインアプリケーション"""
	
	# ページ設定
	st.set_page_config(
		page_title="JourneyMap - 旅の軌跡",
		page_icon="🗺️",
		layout="wide",
		initial_sidebar_state="expanded"
	)
	
	# カスタムCSS
	st.markdown("""
		<style>
		@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
		
		/* テキスト要素のみに日本語フォントを適用（アイコンは除外） */
		body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stSidebar"],
		.stMarkdown, .stText, .stButton, .stMetric, .stExpander, .stHeader,
		p, span, li, label, h1, h2, h3, h4, h5, h6, code, pre {
			font-family: "Noto Sans JP", "Yu Gothic UI", "Meiryo", "Hiragino Kaku Gothic ProN",
				"Hiragino Sans", "Source Han Sans JP", "MS PGothic", "Segoe UI", sans-serif;
			-webkit-font-smoothing: antialiased;
			-moz-osx-font-smoothing: grayscale;
			text-rendering: optimizeLegibility;
		}
		/* Material Icons を元に戻す（矢印などが文字列として表示される問題の修正） */
		.material-icons, .material-icons-outlined, .material-icons-round, .material-icons-sharp, .material-icons-two-tone {
			font-family: 'Material Icons' !important;
			font-weight: normal !important;
			font-style: normal !important;
			text-transform: none !important;
			letter-spacing: normal !important;
			white-space: nowrap !important;
			word-wrap: normal !important;
			direction: ltr !important;
			-webkit-font-feature-settings: 'liga';
			-webkit-font-smoothing: antialiased;
		}
		/* Streamlit主要コンテナにも明示適用 */
		[data-testid="stAppViewContainer"], [data-testid="stSidebar"] {
			font-family: "Noto Sans JP", "Yu Gothic UI", "Meiryo", "Hiragino Kaku Gothic ProN",
				"Hiragino Sans", "Source Han Sans JP", "MS PGothic", "Segoe UI", sans-serif !important;
		}
		.main-header {
			font-size: 2.5rem;
			font-weight: bold;
			color: #2c5aa0;
			text-align: center;
			padding: 1rem 0;
		}
		.sub-header {
			font-size: 1.2rem;
			color: #666;
			text-align: center;
			margin-bottom: 2rem;
		}
		.info-box {
			background-color: #e8f4f8;
			padding: 1rem;
			border-radius: 0.5rem;
			border-left: 4px solid #2c5aa0;
			margin: 1rem 0;
			color: #1f2937; /* dark text for readability */
		}
		.info-box a { color: #1d4ed8; }
		.info-box strong { color: #111827; }

		.success-box {
			background-color: #d4edda;
			padding: 1rem;
			border-radius: 0.5rem;
			border-left: 4px solid #28a745;
			margin: 1rem 0;
			color: #1f2937;
		}
		.success-box a { color: #1d4ed8; }
		.success-box strong { color: #111827; }

		.warning-box {
			background-color: #fff3cd;
			padding: 1rem;
			border-radius: 0.5rem;
			border-left: 4px solid #d97706; /* darker amber */
			margin: 1rem 0;
			color: #1f2937;
		}
		.warning-box a { color: #b45309; }
		.warning-box strong { color: #92400e; }
		</style>
	""", unsafe_allow_html=True)
	
	# セッションステートの初期化
	if 'scanned' not in st.session_state:
		st.session_state.scanned = False
	if 'scan_result' not in st.session_state:
		st.session_state.scan_result = None
	if 'db_stats' not in st.session_state:
		st.session_state.db_stats = None
	# マップ表示用のセッション値
	if 'map_html' not in st.session_state:
		st.session_state.map_html = None
	if 'map_stats' not in st.session_state:
		st.session_state.map_stats = None
	# タイムラインフィルタ用のセッション値
	if 'filtered' not in st.session_state:
		st.session_state.filtered = False
	if 'filter_start' not in st.session_state:
		st.session_state.filter_start = None
	if 'filter_end' not in st.session_state:
		st.session_state.filter_end = None
	# 拡大表示用のセッション値
	if 'show_modal' not in st.session_state:
		st.session_state.show_modal = False
	if 'selected_photo' not in st.session_state:
		st.session_state.selected_photo = None
	# 写真一覧ハイライト用インデックス
	if 'selected_photo_index' not in st.session_state:
		st.session_state.selected_photo_index = None
	# スライドショー用のセッション値
	if 'slideshow_running' not in st.session_state:
		st.session_state.slideshow_running = False
	if 'slideshow_speed' not in st.session_state:
		st.session_state.slideshow_speed = 2.0
	# 自動更新用のセッション値
	if 'auto_update_map' not in st.session_state:
		st.session_state.auto_update_map = False
	if 'auto_update_enabled' not in st.session_state:
		st.session_state.auto_update_enabled = True
	# 表示設定（レイアウト・画質）
	if 'view_mode' not in st.session_state:
		st.session_state.view_mode = "グリッド"
	if 'img_quality' not in st.session_state:
		st.session_state.img_quality = "標準（長辺1024px）"
	
	# ヘッダー
	st.markdown('<div class="main-header">🗺️ JourneyMap</div>', unsafe_allow_html=True)
	st.markdown('<div class="sub-header">写真とマップを融合した思い出管理アプリ</div>', unsafe_allow_html=True)
	
	# サイドバー
	with st.sidebar:
		st.header("📂 写真フォルダ指定")
		
		# フォルダパス入力
		folder_path = st.text_input(
			"フォルダパスを入力",
			placeholder="例: C:\\Users\\YourName\\Pictures",
			help="写真や動画が含まれるフォルダのパスを入力してください"
		)
		
		# スキャン設定
		st.markdown("### ⚙️ スキャン設定")
		recursive = st.checkbox(
			"サブフォルダも探索",
			value=True,
			help="サブフォルダ内のファイルも含めてスキャンします"
		)
		
		# スキャンボタン
		scan_button = st.button(
			"🔍 スキャン開始",
			type="primary",
			use_container_width=True
		)
		
		st.markdown("---")
		
		# タイムラインフィルタ
		st.markdown("---")
		st.markdown("### 📅 タイムラインフィルタ")
		
		db = Database()
		db.initialize()
		photos_for_filter = db.get_all_photos()
		db.close()
		
		if photos_for_filter:
			dated_photos = [p for p in photos_for_filter if p['timestamp']]
			if dated_photos:
				from datetime import datetime
				timestamps = [datetime.fromisoformat(p['timestamp']) for p in dated_photos]
				min_date = min(timestamps).date()
				max_date = max(timestamps).date()
				
				st.write(f"📊 データ期間: {min_date} 〜 {max_date}")
				
				date_range = st.date_input(
					"期間を指定",
					value=(min_date, max_date),
					min_value=min_date,
					max_value=max_date,
					help="表示する写真の期間を指定してください"
				)
				
				if st.button("🔍 フィルタを適用", type="secondary", use_container_width=True):
					if isinstance(date_range, tuple) and len(date_range) == 2:
						start_date, end_date = date_range
						st.session_state.filter_start = start_date
						st.session_state.filter_end = end_date
						st.session_state.filtered = True
						# 自動更新が有効な場合はマップ自動更新フラグを立てる
						if st.session_state.auto_update_enabled:
							st.session_state.auto_update_map = True
						st.success(f"✅ フィルタを適用: {start_date} 〜 {end_date}")
						st.rerun()
					else:
						st.warning("⚠️ 開始日と終了日を両方指定してください")
				
				if st.session_state.filtered:
					if st.button("🔄 フィルタをリセット", use_container_width=True):
						st.session_state.filtered = False
						st.session_state.filter_start = None
						st.session_state.filter_end = None
						# 自動更新が有効な場合はマップ自動更新フラグを立てる
						if st.session_state.auto_update_enabled:
							st.session_state.auto_update_map = True
						st.info("📅 すべての期間を表示します")
						st.rerun()
			else:
				st.info("📅 タイムスタンプ情報がありません")
		else:
			st.info("📅 データがありません")
		
		# 設定
		st.markdown("---")
		st.markdown("### ⚙️ 設定")
		auto_update = st.checkbox(
			"フィルタ変更で自動更新",
			value=st.session_state.auto_update_enabled,
			help="フィルタを変えたときに自動で地図を更新します"
		)
		st.session_state.auto_update_enabled = auto_update
		if not auto_update:
			st.info("💡 手動更新モード: フィルタ適用後、「🗺️ マップを生成」ボタンをクリックしてください")
		
		# 表示設定
		st.markdown("### 🖼️ 表示設定")
		st.session_state.view_mode = st.radio(
			"レイアウト",
			options=["グリッド", "リスト（縦）"],
			horizontal=True
		)
		st.session_state.img_quality = st.selectbox(
			"画像の画質",
			options=["軽量（長辺512px）", "標準（長辺1024px）", "高画質（長辺2048px）", "オリジナル（重い）"],
			index=["軽量（長辺512px）", "標準（長辺1024px）", "高画質（長辺2048px）", "オリジナル（重い）"].index(st.session_state.img_quality)
		)
		if st.session_state.img_quality == "オリジナル（重い）":
			st.caption("⚠️ 通信量・メモリ使用量が増えます。表示が遅い場合は標準以下にしてください。")
		
		# データベースリセット
		st.markdown("### 🗑️ データベース管理")
		if st.button("データベースをリセット", type="secondary"):
			db = Database()
			db.initialize()
			# テーブルを削除して再作成
			db.connect()
			db.conn.execute("DELETE FROM photos")
			db.conn.commit()
			db.close()
			st.session_state.scanned = False
			st.session_state.scan_result = None
			st.session_state.db_stats = None
			st.success("データベースをリセットしました")
			st.rerun()
		
		st.markdown("---")
		
		# ログ表示
		st.markdown("### 📋 ログ")
		
		if st.button("最新ログを表示", use_container_width=True):
			from datetime import datetime
			
			log_dir = Path("data/logs")
			log_file = log_dir / f"journeymap_{datetime.now().strftime('%Y%m%d')}.log"
			
			if log_file.exists():
				try:
					with open(log_file, 'r', encoding='utf-8') as f:
						log_content = f.readlines()
					
					# 最新50行を表示
					recent_logs = log_content[-50:]
					
					st.text_area(
						"最新ログ（最新50行）",
						value=''.join(recent_logs),
						height=300
					)
				except Exception as e:
					st.error(f"ログ読み込みエラー: {e}")
			else:
				st.info("ログファイルがまだ作成されていません")
		
		st.markdown("---")
		
		# キャッシュ管理
		st.markdown("### 🗑️ キャッシュ管理")
		
		if st.button("キャッシュをクリア", use_container_width=True):
			st.cache_data.clear()
			st.success("✅ キャッシュをクリアしました")
			st.info("ページをリロードすると、最新のデータが反映されます")
			st.rerun()
		
		# キャッシュ情報の表示
		with st.expander("📊 キャッシュ情報"):
			st.info("""
			**キャッシュの役割:**
			- データベース読み込みを高速化
			- マップ生成を高速化
			- 同じデータへのアクセスを最適化
			
			**キャッシュの有効期限:**
			- データベース: 5分
			- マップ: 10分
			
			**キャッシュをクリアするタイミング:**
			- 新しい写真をスキャンした後
			- データベースをリセットした後
			- 表示がおかしい場合
			""")
		
		# パフォーマンス表示切り替え
		if 'show_performance' not in st.session_state:
			st.session_state.show_performance = False
		
		show_perf = st.checkbox(
			"パフォーマンス情報を表示",
			value=st.session_state.show_performance
		)
		st.session_state.show_performance = show_perf
		
		st.markdown("---")
		
		# 逆ジオコーディング
		st.markdown("### 🌍 逆ジオコーディング（オプション）")
		
		st.info("""
		GPS座標から場所名を取得します。
		
		**注意:**
		- API制限があるため、大量データには時間がかかります
		- インターネット接続が必要です
		""")
		
		if st.button("場所名を取得", use_container_width=True):
			with st.spinner("🌍 設定されていない写真の場所名を取得中..."):
				try:
					from src.geocoding import ReverseGeocoder
					
					geocoder = ReverseGeocoder()
					
					db = Database()
					db.initialize()
					updated = db.update_location_names(geocoder)
					
					if updated > 0:
						st.success(f"✅ {updated} 件の場所名を取得しました")
						st.cache_data.clear()
						st.rerun()
					else:
						st.info("すべての写真に場所名が設定済みです")
					
				except Exception as e:
					st.error(f"❌ 設定エラー: {e}")
		
		st.markdown("---")
		
		# Google Drive 連携
		st.markdown("### ☁️ Google Drive 連携")
		with st.expander("設定 / 手動同期", expanded=False):
			st.caption("サービスアカウントJSONを Streamlit Secrets の `gcp_service_account` に保存し、このアカウントにフォルダを共有してください。")
			
			drive_folder_id = st.text_input("Drive フォルダID", value=st.session_state.get("drive_folder_id", ""))
			if drive_folder_id:
				st.session_state.drive_folder_id = drive_folder_id
			
			last_synced = st.session_state.get("drive_last_synced", None)
			if last_synced:
				st.info(f"前回同期: {last_synced}")
			
			if st.button("📥 手動同期", use_container_width=True):
				try:
					if "drive_folder_id" not in st.session_state or not st.session_state.drive_folder_id:
						st.error("フォルダIDを入力してください")
					else:
						from src.drive_sync import DriveSync
						from src.scanner import MediaScanner
						
						sync = DriveSync(st.session_state.drive_folder_id)
						res = sync.sync_new_photos(modified_after_iso=last_synced)
						
						if res["downloaded"] > 0:
							with st.spinner("新規ファイルをスキャン・登録中..."):
								scan_result = MediaScanner.scan_folder(sync.download_dir, recursive=False)
								db = Database()
								db.initialize()
								from src.exif_extractor import ExifExtractor
								from src.video_metadata import VideoMetadataExtractor
								db.bulk_insert_from_scanner(scan_result, ExifExtractor, VideoMetadataExtractor)
								db.close()
							st.success(f"✅ {res['downloaded']} 件のファイルを取り込みました")
							st.session_state.drive_last_synced = res.get("latest") or st.session_state.get("drive_last_synced")
							st.cache_data.clear()
							st.rerun()
						else:
							st.info("新しいファイルはありませんでした")
				except Exception as e:
					st.error(f"❌ 同期エラー: {e}")
		
		# 観光地データ管理
		st.markdown("### 🗾 観光地データ")
		
		with st.expander("📥 データインポート"):
			st.info("""
			**初回のみ実行してください**
			
			観光地データ（日本の主要観光地）をインポートします。
			""")
			st.caption("Phase 7-1 の実装指示書は以上です。これを実行後、Phase 7-2 に進みます。")
			if st.button("観光地データをインポート", use_container_width=True):
				with st.spinner("📥 インポート中..."):
					try:
						from src.attraction_importer import AttractionImporter
						from pathlib import Path as _Path
						
						importer = AttractionImporter()
						csv_path = _Path("data/attractions_japan.csv")
						
						if not csv_path.exists():
							st.error(f"❌ CSVファイルが見つかりません: {csv_path}")
						else:
							count = importer.import_from_csv(csv_path)
							st.success(f"✅ {count}件の観光地データをインポートしました")
							st.cache_data.clear()
							st.rerun()
					
					except Exception as e:
						st.error(f"❌ インポートエラー: {e}")
		
		# 自動訪問済み判定
		with st.expander("🔍 訪問済み自動判定"):
			st.info("""
			**写真の位置情報から自動判定**
			
			写真の撮影地点が観光地の近く（500m以内）にある場合、
			その観光地を自動的に「訪問済み」にします。
			""")
			
			col1, col2 = st.columns(2)
			
			with col1:
				threshold = st.number_input(
					"判定距離（km）",
					min_value=0.1,
					max_value=5.0,
					value=0.5,
					step=0.1
				)
			
			with col2:
				st.write("")
			
			if st.button("自動判定を実行", use_container_width=True):
				with st.spinner("🔍 判定中..."):
					try:
						db = Database()
						db.initialize()
						updated = db.auto_mark_visited_attractions(threshold_km=threshold)
						
						if updated > 0:
							st.success(f"✅ {updated}件の観光地を訪問済みに設定しました")
							st.cache_data.clear()
							st.rerun()
						else:
							st.info("ℹ️ 新たに訪問済みになった観光地はありませんでした")
					
					except Exception as e:
						st.error(f"❌ 自動判定エラー: {e}")
		
		# 観光地統計
		db = Database()
		db.initialize()
		
		try:
			total_attractions = len(db.get_attractions_cached())
			visited_attractions = len(db.get_attractions_cached(visited=True))
			unvisited_attractions = len(db.get_attractions_cached(visited=False))
		finally:
			db.close()
		
		if total_attractions > 0:
			col_a1, col_a2, col_a3 = st.columns(3)
			with col_a1:
				st.metric("総数", f"{total_attractions}件")
			with col_a2:
				st.metric("訪問済み", f"{visited_attractions}件")
			with col_a3:
				st.metric("未訪問", f"{unvisited_attractions}件")
		
		st.markdown("---")
		
		# 観光地表示設定
		st.markdown("### 🗺️ マップ表示設定")
		
		# 観光地マーカーの表示/非表示
		show_attractions = st.checkbox(
			"観光地を表示",
			value=False,
			help="マップ上に観光地マーカーを表示します"
		)
		
		if show_attractions:
			# カテゴリフィルタ
			st.markdown("#### カテゴリフィルタ")
			
			# 利用可能なカテゴリを取得
			db = Database()
			db.initialize()
			all_attractions = db.get_attractions_cached()
			
			available_categories = list(set([
				a['category'] for a in all_attractions 
				if a.get('category')
			]))
			available_categories.sort()
			
			if available_categories:
				selected_categories = st.multiselect(
					"表示するカテゴリ",
					available_categories,
					default=available_categories,
					help="表示したいカテゴリを選択してください"
				)
			else:
				selected_categories = []
				st.info("カテゴリ情報がありません")
			
			# 訪問状況フィルタ
			st.markdown("#### 訪問状況フィルタ")
			
			col1, col2 = st.columns(2)
			
			with col1:
				show_visited = st.checkbox("訪問済み", value=True)
			
			with col2:
				show_unvisited = st.checkbox("未訪問", value=True)
			
			# セッションステートに保存
			st.session_state.show_attractions = True
			st.session_state.selected_categories = selected_categories
			st.session_state.show_visited = show_visited
			st.session_state.show_unvisited = show_unvisited
		else:
			st.session_state.show_attractions = False
		
		# ウィッシュリストの表示/非表示
		show_wishlist = st.checkbox(
			"ウィッシュリストを表示",
			value=False,
			help="ウィッシュリストの場所をマップ上に表示します"
		)
		st.session_state.show_wishlist = show_wishlist
		
		st.markdown("---")
		
		# ウィッシュリスト管理
		st.markdown("### 📝 ウィッシュリスト")
		
		db = Database()
		db.initialize()
		wishlist = db.get_wishlist_cached(order_by='priority')
		db.close()
		
		if not wishlist:
			st.info("ウィッシュリストは空です")
			st.markdown("""
			**ウィッシュリストの使い方:**
			
			1. マップ表示設定で「観光地を表示」をON
			2. 未訪問の観光地を下の「観光地一覧」から追加
			""")
		else:
			st.markdown(f"**{len(wishlist)}件の行きたい場所**")
			
			# ソート順の選択
			sort_by = st.radio(
				"並び順",
				["優先度", "名前", "追加日"],
				horizontal=True,
				label_visibility="collapsed"
			)
			
			sort_map = {
				"優先度": "priority",
				"名前": "name",
				"追加日": "created_at"
			}
			
			if sort_by != "優先度":
				st.cache_data.clear()
				wishlist = db.get_wishlist_cached(order_by=sort_map[sort_by])
			
			# ウィッシュリストアイテムの表示
			for item in wishlist:
				with st.expander(f"{'⭐' * item['priority']} {item['name']}", expanded=False):
					st.write(f"**カテゴリ:** {item.get('category', '不明')}")
					st.write(f"**場所:** {item.get('city', '')}, {item.get('prefecture', '')}")
					
					if item.get('rating'):
						st.write(f"**評価:** {'⭐' * int(item['rating'])}")
					
					# 優先度の変更
					new_priority = st.select_slider(
						"優先度",
						options=[1, 2, 3, 4, 5],
						value=item['priority'],
						key=f"priority_{item['id']}"
					)
					
					if new_priority != item['priority']:
						db.update_wishlist_item(item['id'], priority=new_priority)
						st.success("✅ 優先度を更新しました")
						st.cache_data.clear()
						st.rerun()
					
					# メモの表示・編集
					current_notes = item.get('notes', '')
					new_notes = st.text_area(
						"メモ",
						value=current_notes,
						key=f"notes_{item['id']}",
						height=80
					)
					
					if new_notes != current_notes:
						if st.button("💾 メモを保存", key=f"save_notes_{item['id']}"):
							db.update_wishlist_item(item['id'], notes=new_notes)
							st.success("✅ メモを保存しました")
							st.cache_data.clear()
							st.rerun()
					
					# 削除ボタン
					if st.button("🗑️ 削除", key=f"delete_{item['id']}", use_container_width=True):
						db.remove_from_wishlist(item['id'])
						st.success("✅ ウィッシュリストから削除しました")
						st.cache_data.clear()
						st.rerun()
		
		st.markdown("---")
		
		# 観光地一覧（未訪問のみ）
		st.markdown("### 🌟 行きたい場所を探す")
		
		with st.expander("観光地一覧", expanded=False):
			db = Database()
			db.initialize()
			
			# 未訪問の観光地を取得
			unvisited = db.get_attractions_cached(visited=False)
			
			if not unvisited:
				st.info("未訪問の観光地がありません")
			else:
				# カテゴリフィルタ
				categories = list(set([a['category'] for a in unvisited if a.get('category')]))
				categories.sort()
				
				if categories:
					filter_category = st.selectbox(
						"カテゴリで絞り込み",
						["すべて"] + categories
					)
					
					if filter_category != "すべて":
						unvisited = [a for a in unvisited if a['category'] == filter_category]
				
				st.write(f"**{len(unvisited)}件の未訪問観光地**")
				
				# 観光地の表示
				for attraction in unvisited:
					col1, col2 = st.columns([3, 1])
					
					with col1:
						st.write(f"**{attraction['name']}**")
						st.caption(f"{attraction.get('category', '')} | {attraction.get('city', '')}, {attraction.get('prefecture', '')}")
					
					with col2:
						# ウィッシュリストに追加済みか確認
						is_in_list = db.is_in_wishlist(attraction['id'])
						
						if is_in_list:
							st.button("✅", key=f"added_{attraction['id']}", disabled=True)
						else:
							if st.button("➕", key=f"add_{attraction['id']}"):
								db.add_to_wishlist(attraction['id'], priority=3)
								st.success(f"✅ {attraction['name']}をウィッシュリストに追加しました")
								st.cache_data.clear()
								st.rerun()
					
					st.markdown("---")
			
			db.close()
		
		st.markdown("""
		<div class="info-box">
		<strong>💡 ヒント</strong><br>
		GPS情報を含む写真のみが地図に表示されます。
		スマートフォンで撮影した写真がおすすめです。
		</div>
		""", unsafe_allow_html=True)
		
		st.markdown("---")
		st.caption("JourneyMap v1.0")
		st.caption("Phase 4-2: フォルダ指定UI")
	
	# スキャン処理
	if scan_button:
		if not folder_path:
			st.error("❌ フォルダパスを入力してください")
		else:
			# 入力パスのサニタイズ（引用符・余分な空白を除去）
			folder_input = folder_path.strip()
			while len(folder_input) > 0 and folder_input[0] in ('"', "'", '“', '”', '「', '『'):
				folder_input = folder_input[1:]
			while len(folder_input) > 0 and folder_input[-1] in ('"', "'", '“', '”', '」', '』'):
				folder_input = folder_input[:-1]
			
			folder = Path(folder_input).expanduser()
			
			if not folder.exists():
				st.error(f"❌ フォルダが見つかりません: {folder_input}")
			elif not folder.is_dir():
				st.error(f"❌ ディレクトリではありません: {folder_input}")
			else:
				# スキャン実行
				with st.spinner("📂 フォルダをスキャン中..."):
					try:
						scan_result = MediaScanner.scan_folder(folder, recursive=recursive)
						st.session_state.scan_result = scan_result
					except Exception as e:
						from src.logger import get_logger
						logger = get_logger()
						logger.error(f"スキャンエラー: {folder_path}")
						
						st.error(f"""
						❌ **スキャンエラーが発生しました**
						
						**フォルダ:** {folder_path}
						
						**考えられる原因:**
						- フォルダへのアクセス権限がない
						- ファイルが破損している
						- サポートされていないファイル形式
						
						**対処方法:**
						1. フォルダのパスを確認してください
						2. フォルダのアクセス権限を確認してください
						3. 別のフォルダで試してください
						
						エラーの詳細はログファイル（data/logs/）を確認してください。
						""")
						return
				
				# データベースに登録
				if scan_result['total'] > 0:
					with st.spinner("💾 データベースに登録中..."):
						db = Database()
						db.initialize()
						
						insert_result = db.bulk_insert_from_scanner(
							scan_result,
							ExifExtractor,
							VideoMetadataExtractor
						)
						
						st.session_state.db_stats = insert_result
						st.session_state.scanned = True
						
						db.close()
					
					st.success("✅ スキャンと登録が完了しました")
					st.rerun()
				else:
					st.warning("⚠️ メディアファイルが見つかりませんでした")
	
	# メインエリア
	if st.session_state.scanned and st.session_state.scan_result:
		# スキャン結果表示
		st.markdown("## 📊 スキャン結果")
		
		scan_result = st.session_state.scan_result
		db_stats = st.session_state.db_stats
		
		col1, col2, col3, col4 = st.columns(4)
		
		with col1:
			st.metric(
				label="📁 検出ファイル",
				value=f"{scan_result['total']} 件",
				delta=f"画像 {len(scan_result['images'])} / 動画 {len(scan_result['videos'])}"
			)
		
		with col2:
			st.metric(
				label="✅ 登録成功",
				value=f"{db_stats['success']} 件",
				delta="新規登録"
			)
		
		with col3:
			st.metric(
				label="⏭️ スキップ",
				value=f"{db_stats['skipped']} 件",
				delta="既登録 / GPS情報なし"
			)
		
		with col4:
			st.metric(
				label="❌ エラー",
				value=f"{db_stats['errors']} 件",
				delta="処理失敗"
			)
		
		# 補足メッセージ
		if db_stats['success'] == 0 and db_stats['skipped'] > 0:
			st.info("💡 すでに登録済みのためスキップされた可能性があります。マップが表示できていればGPS情報は取得済みです。")
		
		st.markdown("---")
		
		# データベース統計（キャッシュ版を使用）
		st.markdown("## 🗄️ データベース統計")
		
		db = Database()
		db.initialize()
		total_photos = db.count_photos_cached()  # キャッシュ版を使用
		
		if total_photos > 0:
			photos = db.get_all_photos_cached()  # キャッシュ版を使用
			
			# 種類別集計
			images = [p for p in photos if p['file_type'] == 'image']
			videos = [p for p in photos if p['file_type'] == 'video']
			
			col1, col2, col3 = st.columns(3)
			
			with col1:
				st.metric("📷 総登録数", f"{total_photos} 件")
			
			with col2:
				st.metric("🖼️ 画像", f"{len(images)} 件")
			
			with col3:
				st.metric("🎬 動画", f"{len(videos)} 件")
			
			# サンプル表示
			st.markdown("### 📋 登録データ（最新5件）")
			
			for photo in photos[-5:][::-1]:
				with st.expander(f"{Path(photo['file_path']).name}"):
					col_a, col_b = st.columns(2)
					
					with col_a:
						st.write(f"**種類:** {photo['file_type']}")
						st.write(f"**日時:** {photo['timestamp'] or '不明'}")
					
					with col_b:
						st.write(f"**緯度:** {photo['latitude']:.6f}")
						st.write(f"**経度:** {photo['longitude']:.6f}")
		else:
			st.info("📭 データベースにデータがありません")
		
		db.close()
		
		st.markdown("---")
		
		# 自動マップ更新
		if 'auto_update_map' in st.session_state and st.session_state.auto_update_map:
			# 一度だけ処理するためにフラグを下げる
			st.session_state.auto_update_map = False
			with st.spinner("🗺️ マップを自動更新中..."):
				try:
					from src.map_generator import MapGenerator
					from datetime import datetime
					
					# データベースから写真データを取得（キャッシュ版）
					db = Database()
					db.initialize()
					all_photos = db.get_all_photos_cached()  # キャッシュ版を使用
					db.close()
					
					# フィルタ適用
					if st.session_state.filtered and st.session_state.filter_start and st.session_state.filter_end:
						start_date = st.session_state.filter_start
						end_date = st.session_state.filter_end
						photos = []
						for p in all_photos:
							if p['timestamp']:
								pd = datetime.fromisoformat(p['timestamp']).date()
								if start_date <= pd <= end_date:
									photos.append(p)
						if len(photos) == 0:
							st.warning("⚠️ 指定した期間に写真がありません")
						else:
							# GPS情報を持つ写真のみを使用
							valid_photos = [p for p in photos if p.get('latitude') is not None and p.get('longitude') is not None]
							if len(valid_photos) == 0:
								st.warning("⚠️ 指定した期間にGPS情報を含む写真がありません")
							else:
								# マップを生成（キャッシュ版）
								photos_hash = MapGenerator._calculate_photos_hash(valid_photos)
								map_html = MapGenerator.generate_map_cached(valid_photos, _photos_hash=photos_hash)
								
								# マップ統計を計算
								generator = MapGenerator()
								center = generator.calculate_center_from_photos(valid_photos)
								zoom = generator.calculate_zoom_level(valid_photos)
								marker_count = len(valid_photos)
								route_points = len(valid_photos)
								
								st.session_state.map_html = map_html
								st.session_state.map_stats = {
									'markers': marker_count,
									'route_points': route_points,
									'center': center,
									'zoom': zoom,
									'total_photos': len(valid_photos),
									'filtered': True
								}
								st.success(f"✅ フィルタ適用済みマップを自動更新（{len(valid_photos)} 件）")
					else:
						photos = all_photos
						
						# GPS情報を持つ写真のみを使用
						valid_photos = [p for p in photos if p.get('latitude') is not None and p.get('longitude') is not None]
						if len(valid_photos) == 0:
							st.warning("⚠️ GPS情報を含む写真がありません")
						else:
							# マップを生成（キャッシュ版）
							photos_hash = MapGenerator._calculate_photos_hash(valid_photos)
							map_html = MapGenerator.generate_map_cached(valid_photos, _photos_hash=photos_hash)
							
							# マップ統計を計算
							generator = MapGenerator()
							center = generator.calculate_center_from_photos(valid_photos)
							zoom = generator.calculate_zoom_level(valid_photos)
							marker_count = len(valid_photos)
							route_points = len(valid_photos)
							
							st.session_state.map_html = map_html
							st.session_state.map_stats = {
								'markers': marker_count,
								'route_points': route_points,
								'center': center,
								'zoom': zoom,
								'total_photos': len(valid_photos),
								'filtered': False
							}
							st.success(f"✅ マップを自動更新（全期間: {len(valid_photos)} 件）")
				except Exception as e:
						from src.logger import get_logger
						logger = get_logger()
						logger.error("マップ生成エラー")
						
						st.error(f"""
						❌ **マップ生成エラーが発生しました**
						
						**考えられる原因:**
						- GPS情報を含む写真がない
						- データベースが破損している
						- メモリ不足
						
						**対処方法:**
						1. GPS情報を含む写真があることを確認してください
						2. データベースをリセットしてみてください
						3. フィルタ範囲を狭めてみてください
						
						エラーの詳細はログファイル（data/logs/）を確認してください。
						""")
		
		# マップ生成セクション
		st.markdown("## 🗺️ マップ生成")
		
		if total_photos > 0:
			st.info(f"📍 {total_photos} 件の写真からマップを生成します")
			
			# マップ生成ボタン（フィルタ対応）
			if st.button("🗺️ マップを生成", type="primary", use_container_width=True):
				with st.spinner("🗺️ マップを生成中..."):
					try:
						from src.map_generator import MapGenerator
						from datetime import datetime
						
						# データベースから写真データを取得（キャッシュ版）
						db = Database()
						db.initialize()
						all_photos = db.get_all_photos_cached()  # キャッシュ版を使用
						db.close()
						
						# フィルタリング処理
						if st.session_state.filtered and st.session_state.filter_start and st.session_state.filter_end:
							start_date = st.session_state.filter_start
							end_date = st.session_state.filter_end
							
							photos = []
							for photo in all_photos:
								if photo['timestamp']:
									photo_date = datetime.fromisoformat(photo['timestamp']).date()
									if start_date <= photo_date <= end_date:
										photos.append(photo)
							
							if len(photos) == 0:
								st.warning("⚠️ 指定した期間に写真がありません")
								st.stop()
							
							st.info(f"📅 フィルタ適用中: {start_date} 〜 {end_date}（{len(photos)} 件）")
						else:
							photos = all_photos
						
						# GPS情報を持つ写真のみを使用
						valid_photos = [photo for photo in photos if photo.get('latitude') is not None and photo.get('longitude') is not None]
						if len(valid_photos) == 0:
							st.warning("⚠️ GPS情報を含む写真がありません")
							st.stop()
						
						# マップを生成（キャッシュ版）
						photos_hash = MapGenerator._calculate_photos_hash(valid_photos)
						map_html = MapGenerator.generate_map_cached(valid_photos, _photos_hash=photos_hash)
						
						# 観光地マーカーを追加（キャッシュを使わない、リアルタイム生成）
						if 'show_attractions' in st.session_state and st.session_state.show_attractions:
							db2 = Database()
							db2.initialize()
							
							# カテゴリでフィルタ
							all_attractions = db2.get_attractions_cached()
							selected_categories = st.session_state.get('selected_categories', [])
							
							if selected_categories:
								filtered_attractions = [
									a for a in all_attractions
									if a.get('category') in selected_categories
								]
							else:
								filtered_attractions = all_attractions
							
							# 観光地マーカーを追加
							if filtered_attractions:
								# 中心/ズームを算出
								_tmp = MapGenerator()
								_center = _tmp.calculate_center_from_photos(valid_photos)
								_zoom = _tmp.calculate_zoom_level(valid_photos)
								
								# 新しいMapGeneratorインスタンスでリアルタイム生成
								gen2 = MapGenerator()
								gen2.create_base_map(
									center_lat=_center[0],
									center_lon=_center[1],
									zoom_start=_zoom
								)
								# 写真マーカー
								gen2.add_markers(valid_photos)
								# ルート
								gen2.add_route(valid_photos, color='#FF6B35', weight=4, opacity=0.8)
								# 観光地マーカー
								gen2.add_attraction_markers(
									filtered_attractions,
									show_visited=st.session_state.get('show_visited', True),
									show_unvisited=st.session_state.get('show_unvisited', True)
								)
								# HTML差し替え
								map_html = gen2.map._repr_html_()
							
							db2.close()
						
						# ウィッシュリストマーカーを追加
						_show_wishlist = st.session_state.get('show_wishlist', False)
						if _show_wishlist:
							db3 = Database()
							db3.initialize()
							wishlist_items = db3.get_wishlist_cached()
							
							if wishlist_items:
								# 既存の gen2 があればそれを使う、なければ新規に作成
								if 'gen2' in locals():
									genW = gen2
								else:
									_tmp2 = MapGenerator()
									_center2 = _tmp2.calculate_center_from_photos(valid_photos)
									_zoom2 = _tmp2.calculate_zoom_level(valid_photos)
									
									genW = MapGenerator()
									genW.create_base_map(
										center_lat=_center2[0],
										center_lon=_center2[1],
										zoom_start=_zoom2
									)
									genW.add_markers(valid_photos)
									genW.add_route(valid_photos, color='#FF6B35', weight=4, opacity=0.8)
								
								genW.add_wishlist_markers(wishlist_items)
								map_html = genW.map._repr_html_()
							
							db3.close()
						
						# ルートプレビューを追加
						_gen_for_route = None
						if 'genW' in locals():
							_gen_for_route = genW
						elif 'gen2' in locals():
							_gen_for_route = gen2
						
						if 'optimized_route' in st.session_state and st.session_state.optimized_route:
							if _gen_for_route is None:
								_tmp3 = MapGenerator()
								_center3 = _tmp3.calculate_center_from_photos(valid_photos)
								_zoom3 = _tmp3.calculate_zoom_level(valid_photos)
								_gen_for_route = MapGenerator()
								_gen_for_route.create_base_map(center_lat=_center3[0], center_lon=_center3[1], zoom_start=_zoom3)
								_gen_for_route.add_markers(valid_photos)
								_gen_for_route.add_route(valid_photos, color='#FF6B35', weight=4, opacity=0.8)
							_gen_for_route.add_route_preview_markers(
								st.session_state.optimized_route,
								color='#FF6B35',
								show_numbers=True
							)
							map_html = _gen_for_route.map._repr_html_()
						elif 'daily_routes' in st.session_state and st.session_state.daily_routes:
							if _gen_for_route is None:
								_tmp4 = MapGenerator()
								_center4 = _tmp4.calculate_center_from_photos(valid_photos)
								_zoom4 = _tmp4.calculate_zoom_level(valid_photos)
								_gen_for_route = MapGenerator()
								_gen_for_route.create_base_map(center_lat=_center4[0], center_lon=_center4[1], zoom_start=_zoom4)
								_gen_for_route.add_markers(valid_photos)
								_gen_for_route.add_route(valid_photos, color='#FF6B35', weight=4, opacity=0.8)
							colors = ['#FF6B35', '#4ECDC4', '#95E1D3', '#FFD93D', '#6BCF7F']
							for day_num, (day_route, _) in enumerate(st.session_state.daily_routes):
								_color = colors[day_num % len(colors)]
								_gen_for_route.add_route_preview_markers(
									day_route,
									color=_color,
									show_numbers=True
								)
							map_html = _gen_for_route.map._repr_html_()
						
						# マップ統計を計算
						generator = MapGenerator()
						center = generator.calculate_center_from_photos(valid_photos)
						zoom = generator.calculate_zoom_level(valid_photos)
						marker_count = len(valid_photos)
						route_points = len(valid_photos)
						
						# セッションステートに保存
						st.session_state.map_html = map_html
						st.session_state.map_stats = {
							'markers': marker_count,
							'route_points': route_points,
							'center': center,
							'zoom': zoom,
							'total_photos': len(valid_photos),
							'filtered': bool(st.session_state.filtered)
						}
						
						if st.session_state.map_stats['filtered']:
							st.success(f"✅ フィルタ適用済みマップを生成（{len(photos)} 件）")
						else:
							st.success(f"✅ マップを生成しました（マーカー: {marker_count}件、ルート: {route_points}点）")
						
						st.rerun()
						
					except Exception as e:
						from src.logger import get_logger
						logger = get_logger()
						logger.error("マップ生成エラー")
						
						st.error(f"""
						❌ **マップ生成エラーが発生しました**
						
						**考えられる原因:**
						- GPS情報を含む写真がない
						- データベースが破損している
						- メモリ不足
						
						**対処方法:**
						1. GPS情報を含む写真があることを確認してください
						2. データベースをリセットしてみてください
						3. フィルタ範囲を狭めてみてください
						
						エラーの詳細はログファイル（data/logs/）を確認してください。
						""")
		else:
			st.warning("📭 マップを生成するには、まず写真をスキャンしてください")
		
		# マップ表示セクション
		if 'map_html' in st.session_state and st.session_state.map_html:
			st.markdown("---")
			st.markdown("## 🗺️ インタラクティブマップ")
			
			# マップ統計
			if 'map_stats' in st.session_state and st.session_state.map_stats:
				stats = st.session_state.map_stats
				
				# フィルタ情報表示
				if stats.get('filtered', False):
					st.info(f"📅 フィルタ適用中: {st.session_state.filter_start} 〜 {st.session_state.filter_end}（{stats.get('total_photos', 0)} 件）")
				
				col1, col2, col3, col4 = st.columns(4)
				
				with col1:
					st.metric("📍 マーカー", f"{stats['markers']} 件")
				
				with col2:
					st.metric("🚶 ルートポイント", f"{stats['route_points']} 件")
				
				with col3:
					st.metric("🌍 中心座標", f"({stats['center'][0]:.4f}, {stats['center'][1]:.4f})")
				
				with col4:
					st.metric("🔍 ズームレベル", f"{stats['zoom']}")
			
			st.markdown("---")
			
			# マーカークリック案内
			st.info("""
			💡 **マップの使い方:**
			- マーカーをクリックすると撮影情報のポップアップが表示されます
			- 写真の詳細は下の「📸 写真一覧」で確認できます
			- マーカーの色: 🔴 写真 / 🔵 動画 / 🟣 ウィッシュリスト
			""")
			
			# Foliumマップを埋め込み
			st.components.v1.html(
				st.session_state.map_html,
				height=600,
				scrolling=True
			)
			
			# 操作ガイド
			st.markdown("""
			<div class="info-box">
			<strong>🎮 マップの操作方法</strong><br>
			• ドラッグで地図を移動<br>
			• スクロールでズームイン/アウト<br>
			• マーカーをクリックでポップアップ表示<br>
			• マーカーにホバーでファイル名表示
			</div>
			""", unsafe_allow_html=True)
			
			# 写真一覧パネル
			st.markdown("---")
			st.markdown("## 📸 写真一覧（時系列）")
			
			# データベースから写真を取得（フィルタを考慮）
			db = Database()
			db.initialize()
			
			if st.session_state.filtered and st.session_state.filter_start and st.session_state.filter_end:
				start_date = st.session_state.filter_start
				end_date = st.session_state.filter_end
				
				all_photos = db.get_all_photos()
				
				from datetime import datetime
				filtered_photos = []
				for photo in all_photos:
					if photo['timestamp']:
						photo_date = datetime.fromisoformat(photo['timestamp']).date()
						if start_date <= photo_date <= end_date:
							filtered_photos.append(photo)
				
				photos_list = filtered_photos
			else:
				photos_list = db.get_all_photos()
			
			db.close()
			
			if photos_list:
				st.info(f"📊 表示中: {len(photos_list)} 件")
				
				# 画像と動画を時系列でマージ
				all_media = sorted(photos_list, key=lambda x: x['timestamp'] or '')
				
				cols_per_row = 1 if st.session_state.view_mode == "リスト（縦）" else 4
				for i in range(0, len(all_media), cols_per_row):
					cols = st.columns(cols_per_row)
					
					for j, col in enumerate(cols):
						idx = i + j
						if idx < len(all_media):
							media = all_media[idx]
							with col:
								# ハイライト表示判定
								is_selected = False
								if 'selected_photo_index' in st.session_state and st.session_state.selected_photo_index is not None:
                                    # ハイライトの対象は時系列インデックス基準に変更
									if st.session_state.selected_photo_index == idx:
										is_selected = True
										st.markdown("""
										<div style="border: 3px solid #FF6B35; border-radius: 8px; padding: 5px; background-color: #FFF3E0;">
										""", unsafe_allow_html=True)
								try:
									from pathlib import Path as _P
									from src.video_thumbnail import VideoThumbnailGenerator
									
									media_path = _P(media['file_path'])
									
									if media_path.exists():
										if media['file_type'] == 'image':
											# 画質設定を解決
											if st.session_state.img_quality.startswith("軽量"):
												long_edge, q = 512, 85
											elif st.session_state.img_quality.startswith("標準"):
												long_edge, q = 1024, 90
											elif st.session_state.img_quality.startswith("高画質"):
												long_edge, q = 2048, 92
											else:
												long_edge, q = 0, 92  # オリジナル
											mt = media_path.stat().st_mtime
											img_bytes = load_resized_image_bytes(str(media_path), long_edge, q, mt)
											st.image(img_bytes, use_container_width=True)
											st.caption(f"📷 {media_path.name}")
										elif media['file_type'] == 'video':
											thumb = VideoThumbnailGenerator.generate_thumbnail(media_path)
											if thumb and thumb.exists():
												mt_t = thumb.stat().st_mtime
												img_bytes = load_resized_image_bytes(str(thumb), 1024, 90, mt_t)
												st.image(img_bytes, use_container_width=True)
												st.caption(f"🎬 {media_path.name}")
											else:
												st.image("https://via.placeholder.com/300x200?text=Video", use_container_width=True)
												st.caption(f"🎬 {media_path.name}")
										else:
											st.image("https://via.placeholder.com/300x200?text=Unknown", use_container_width=True)
											st.caption(f"{media_path.name}")
										
										with st.expander("詳細情報", expanded=is_selected):
											st.write(f"**種類:** {media['file_type']}")
											st.write(f"**撮影日時:** {media['timestamp'] or '不明'}")
											if media.get('location_name'):
												st.write(f"**📍 場所:** {media['location_name']}")
											st.write(f"**緯度:** {media['latitude']:.6f}")
											st.write(f"**経度:** {media['longitude']:.6f}")
											st.write(f"**ファイル:** {media_path.name}")
											
											if media['file_type'] == 'image':
												if st.button("🔍 拡大表示", key=f"view_{idx}"):
													st.session_state.selected_photo = media
													st.session_state.selected_photo_index = idx
													st.session_state.show_modal = True
													st.rerun()
											elif media['file_type'] == 'video':
												if st.button("▶️ 再生", key=f"play_{idx}"):
													st.session_state.selected_video = media
													st.session_state.show_video_modal = True
													st.rerun()
									else:
										st.warning("ファイルが見つかりません")
								except Exception as e:
									st.error(f"読み込みエラー: {e}")
								finally:
									if is_selected:
										st.markdown("</div>", unsafe_allow_html=True)
			else:
				st.info("📭 表示するメディアがありません")
		
		# ルート生成機能（ウィッシュリストがある場合のみ表示）
		db = Database()
		db.initialize()
		wishlist = db.get_wishlist_cached()
		db.close()
		
		if wishlist and len(wishlist) >= 2:
			st.markdown("---")
			st.markdown("## 🗺️ おすすめルート生成")
			
			st.info(f"""
			**ウィッシュリストから最適なルートを自動生成します**
			
			- 現在のウィッシュリスト: **{len(wishlist)}件**
			- 最短距離で全地点を回るルートを計算します
			""")
			
			col_r1, col_r2, col_r3 = st.columns(3)
			
			with col_r1:
				# 開始地点の選択
				start_location_names = [item['name'] for item in wishlist]
				start_location = st.selectbox(
					"開始地点",
					start_location_names,
					help="旅行の開始地点を選択してください"
				)
				start_index = start_location_names.index(start_location)
			
			with col_r2:
				# 日数の設定
				days = st.number_input(
					"旅行日数",
					min_value=1,
					max_value=30,
					value=1,
					help="複数日の場合、1日あたりの訪問地点数を自動調整します"
				)
			
			with col_r3:
				# 移動速度の設定
				speed = st.number_input(
					"平均速度 (km/h)",
					min_value=10,
					max_value=100,
					value=40,
					help="移動時間の推定に使用します"
				)
			
			# ルート生成ボタン
			if st.button("🗺️ ルートを生成", use_container_width=True, type="primary"):
				with st.spinner("🧭 最適ルートを計算中..."):
					try:
						from src.route_optimizer import RouteOptimizer
						
						optimizer = RouteOptimizer()
						
						if days == 1:
							# 1日の旅程
							optimized_route, total_distance = optimizer.optimize_route(
								wishlist,
								start_index=start_index
							)
							
							# 推定移動時間
							travel_time = optimizer.estimate_travel_time(total_distance, speed)
							
							st.success(f"✅ 最適ルートを生成しました")
							
							# サマリー表示
							s1, s2, s3 = st.columns(3)
							with s1:
								st.metric("訪問地点数", f"{len(optimized_route)}箇所")
							with s2:
								st.metric("総距離", f"{total_distance:.1f} km")
							with s3:
								st.metric("推定移動時間", f"{travel_time:.1f} 時間")
							
							# ルート詳細
							st.markdown("### 📍 ルート詳細")
							
							for i, location in enumerate(optimized_route, 1):
								rc1, rc2, rc3 = st.columns([1, 4, 2])
								
								with rc1:
									if i == 1:
										st.markdown(f"**🚩 {i}**")
									elif i == len(optimized_route):
										st.markdown(f"**🏁 {i}**")
									else:
										st.markdown(f"**{i}**")
								
								with rc2:
									st.write(f"**{location['name']}**")
									st.caption(f"{location.get('category', '')} | {location.get('city', '')}")
								
								with rc3:
									if i < len(optimized_route):
										next_location = optimized_route[i]
										distance = RouteOptimizer.calculate_distance(
											location['latitude'], location['longitude'],
											next_location['latitude'], next_location['longitude']
										)
										st.caption(f"↓ {distance:.1f} km")
							
							# セッションステートに保存（マップ表示用）
							st.session_state.optimized_route = optimized_route
							st.session_state.route_total_distance = total_distance
							
						else:
							# 複数日の旅程
							daily_routes = optimizer.split_route_by_days(
								wishlist,
								days=days,
								start_index=start_index
							)
							
							st.success(f"✅ {days}日間の旅程を生成しました")
							
							# 各日の旅程を表示
							for day_num, (day_route, day_distance) in enumerate(daily_routes, 1):
								with st.expander(f"📅 {day_num}日目 - {len(day_route)}箇所, {day_distance:.1f} km", expanded=True):
									day_travel_time = optimizer.estimate_travel_time(day_distance, speed)
									
									dc1, dc2, dc3 = st.columns(3)
									with dc1:
										st.metric("訪問地点数", f"{len(day_route)}箇所")
									with dc2:
										st.metric("総距離", f"{day_distance:.1f} km")
									with dc3:
										st.metric("推定移動時間", f"{day_travel_time:.1f} 時間")
									
									# この日のルート詳細
									for i, location in enumerate(day_route, 1):
										ec1, ec2, ec3 = st.columns([1, 4, 2])
										with ec1:
											if i == 1:
												st.markdown(f"**🚩 {i}**")
											elif i == len(day_route):
												st.markdown(f"**🏁 {i}**")
											else:
												st.markdown(f"**{i}**")
										with ec2:
											st.write(f"**{location['name']}**")
											st.caption(f"{location.get('category', '')} | {location.get('city', '')}")
										with ec3:
											if i < len(day_route):
												next_location = day_route[i]
												distance = RouteOptimizer.calculate_distance(
													location['latitude'], location['longitude'],
													next_location['latitude'], next_location['longitude']
												)
												st.caption(f"↓ {distance:.1f} km")
							
							# セッションステートに保存
							st.session_state.daily_routes = daily_routes
							st.session_state.route_days = days
					
					except Exception as e:
						st.error(f"❌ ルート生成エラー: {e}")
						from src.logger import get_logger
						logger = get_logger()
						logger.error("ルート生成エラー")
			
			# ルートクリア
			if 'optimized_route' in st.session_state or 'daily_routes' in st.session_state:
				if st.button("🗑️ ルート表示をクリア", use_container_width=True):
					if 'optimized_route' in st.session_state:
						del st.session_state.optimized_route
					if 'route_total_distance' in st.session_state:
						del st.session_state.route_total_distance
					if 'daily_routes' in st.session_state:
						del st.session_state.daily_routes
					if 'route_days' in st.session_state:
						del st.session_state.route_days
					
					st.success("✅ ルート表示をクリアしました")
					st.rerun()
		
		# 次のステップ案内
		st.markdown("""
		<div class="success-box">
		<strong>✅ 次のステップ</strong><br>
		Phase 4-3 でマップを表示できるようになります！
		</div>
		""", unsafe_allow_html=True)
	
	else:
		# 初期画面
		st.markdown("## 🚀 アプリケーションステータス")
		
		db = Database()
		db.initialize()
		total_photos = db.count_photos()
		db.close()
		
		col1, col2, col3 = st.columns(3)
		
		with col1:
			st.metric(
				label="📊 登録済み写真",
				value=f"{total_photos} 件"
			)
		
		with col2:
			st.metric(
				label="🗺️ マップポイント",
				value=f"{total_photos} 件"
			)
		
		with col3:
			st.metric(
				label="📅 期間",
				value="未指定",
				delta="Phase 4-4 で実装"
			)
		
		st.markdown("---")
		
		# パフォーマンス測定
		if 'show_performance' in st.session_state and st.session_state.show_performance:
			st.markdown("### ⚡ パフォーマンス")
			
			import time
			
			# データベース読み込み速度
			start = time.time()
			db = Database()
			db.initialize()
			photos = db.get_all_photos_cached()
			db.close()
			db_time = time.time() - start
			
			col1, col2 = st.columns(2)
			
			with col1:
				st.metric("データベース読み込み", f"{db_time*1000:.1f}ms")
			
			with col2:
				st.metric("総データ数", f"{len(photos)} 件")
		
		# 使い方ガイド
		st.markdown("## 📖 使い方")
		
		st.markdown("""
		### 1. 写真フォルダを指定
		サイドバーにフォルダのパスを入力します。
		
		### 2. スキャン開始
		「🔍 スキャン開始」を押すと、写真と動画を検索します。
		
		### 3. 自動登録
		GPS情報を持つファイルだけをデータベースに登録します。
		
		### 4. マップ表示
		「🗺️ マップを生成」で地図にマーカーとルートを表示します。
		""")
		
		st.markdown("---")
		
		st.markdown("""
		<div class="warning-box">
		<strong>⚠️ 注意</strong><br>
		GPS情報を含まない写真はスキップされます。<br>
		スマートフォンで「位置情報タグ」をONにして撮影した写真を使用してください。
		</div>
		""", unsafe_allow_html=True)


if __name__ == "__main__":
	main()


# 拡大表示モーダル（改善版）
if 'show_modal' in st.session_state and st.session_state.show_modal:
	if 'selected_photo' in st.session_state and 'selected_photo_index' in st.session_state:
		photo = st.session_state.selected_photo
		current_index = st.session_state.selected_photo_index
		
		from pathlib import Path as _PM
		from PIL import Image as _IM
		
		# 対象写真のパス
		img_path = _PM(photo['file_path'])
		
		st.markdown("---")
		st.markdown("## 🖼️ 拡大表示")
		
		# ナビゲーションボタン列
		col_nav1, col_nav2, col_nav3, col_nav4, col_nav5 = st.columns([1,1,1,1,1])
		
		# データベースから（現在のフィルタ条件に基づいた）画像リストを取得
		db = Database()
		db.initialize()
		if st.session_state.filtered and st.session_state.filter_start and st.session_state.filter_end:
			start_date = st.session_state.filter_start
			end_date = st.session_state.filter_end
			all_p = db.get_all_photos()
			from datetime import datetime as _DT
			flt = []
			for p in all_p:
				if p['timestamp']:
					d = _DT.fromisoformat(p['timestamp']).date()
					if start_date <= d <= end_date:
						flt.append(p)
			photos_list = flt
		else:
			photos_list = db.get_all_photos()
		db.close()
		
		image_photos = [p for p in photos_list if p['file_type'] == 'image']
		total_images = len(image_photos)
		# 安全確保
		if total_images == 0:
			st.warning("表示可能な画像がありません")
		else:
			# ナビゲーション
			with col_nav1:
				if st.button("⏮️ 最初", use_container_width=True, disabled=(current_index == 0)):
					st.session_state.selected_photo_index = 0
					st.session_state.selected_photo = image_photos[0]
					st.rerun()
			with col_nav2:
				if st.button("◀️ 前へ", use_container_width=True, disabled=(current_index == 0)):
					st.session_state.selected_photo_index = current_index - 1
					st.session_state.selected_photo = image_photos[current_index - 1]
					st.rerun()
			with col_nav3:
				st.markdown(f"<div style='text-align:center; padding:8px; font-weight:bold;'>{current_index + 1} / {total_images}</div>", unsafe_allow_html=True)
			with col_nav4:
				if st.button("▶️ 次へ", use_container_width=True, disabled=(current_index >= total_images - 1)):
					st.session_state.selected_photo_index = current_index + 1
					st.session_state.selected_photo = image_photos[current_index + 1]
					st.rerun()
			with col_nav5:
				if st.button("⏭️ 最後", use_container_width=True, disabled=(current_index >= total_images - 1)):
					st.session_state.selected_photo_index = total_images - 1
					st.session_state.selected_photo = image_photos[total_images - 1]
					st.rerun()
			
			st.markdown("---")
			
			# メイン表示
			col1, col2 = st.columns([3,1])
			with col1:
				if img_path.exists():
					try:
						img = _IM.open(img_path)
						st.image(img, use_container_width=True)
					except Exception as e:
						st.error(f"画像読み込みエラー: {e}")
				else:
					st.warning("画像が見つかりません")
				
				# スライドショー
				st.markdown("---")
				col_ss1, col_ss2, col_ss3 = st.columns([1,1,1])
				with col_ss1:
					if not st.session_state.slideshow_running:
						if st.button("▶️ スライドショー開始", use_container_width=True):
							st.session_state.slideshow_running = True
							st.rerun()
					else:
						if st.button("⏸️ 一時停止", use_container_width=True):
							st.session_state.slideshow_running = False
							st.rerun()
				with col_ss2:
					speed = st.selectbox("速度", options=[1.0, 2.0, 3.0, 5.0], index=([1.0,2.0,3.0,5.0].index(st.session_state.slideshow_speed) if st.session_state.slideshow_speed in [1.0,2.0,3.0,5.0] else 1), format_func=lambda x: f"{x}秒")
					st.session_state.slideshow_speed = speed
				with col_ss3:
					st.markdown("<div style='padding: 8px;'></div>", unsafe_allow_html=True)
					st.info("⌨️ キーボード: ← →")
				
				# 実行
				if st.session_state.slideshow_running and total_images > 0:
					import time as _t
					_t.sleep(st.session_state.slideshow_speed)
					if current_index < total_images - 1:
						st.session_state.selected_photo_index = current_index + 1
						st.session_state.selected_photo = image_photos[current_index + 1]
					else:
						st.session_state.selected_photo_index = 0
						st.session_state.selected_photo = image_photos[0]
					st.rerun()
			
			with col2:
				st.markdown("### 📋 詳細情報")
				st.write("**ファイル番号:**")
				st.code(f"{current_index + 1} / {total_images}")
				st.write("**ファイル名:**")
				st.code(_PM(photo['file_path']).name)
				st.write("**撮影日時:**")
				st.write(photo['timestamp'] or '不明')
				if photo.get('location_name'):
					st.write("**📍 場所:**")
					st.write(photo['location_name'])
				st.write("**位置情報:**")
				st.write(f"緯度: {photo['latitude']:.6f}")
				st.write(f"経度: {photo['longitude']:.6f}")
				st.write("**ファイルパス:**")
				st.code(photo['file_path'], language=None)
				
				if st.button("🗺️ 地図で表示", use_container_width=True):
					st.info("マップをスクロールして該当位置を確認してください")
				
				st.markdown("---")
				if st.button("✖️ 閉じる", type="primary", use_container_width=True):
					st.session_state.show_modal = False
					st.session_state.selected_photo = None
					st.session_state.selected_photo_index = None
					st.session_state.slideshow_running = False
					st.rerun()
		
		st.markdown("---")

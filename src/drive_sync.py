"""
Google Drive 同期モジュール
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import io
from datetime import datetime, timezone

import streamlit as st

try:
	from google.oauth2 import service_account
	from googleapiclient.discovery import build
	from googleapiclient.http import MediaIoBaseDownload
except Exception:
	# Streamlit Cloud 上でまだ依存が入っていない場合に備える
	service_account = None
	build = None
	MediaIoBaseDownload = None


SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


class DriveSync:
	"""Google Drive から写真を同期するクラス"""
	
	def __init__(self, folder_id: str, download_dir: Path = Path("data/drive_import")):
		self.folder_id = folder_id
		self.download_dir = Path(download_dir)
		self.download_dir.mkdir(parents=True, exist_ok=True)
	
	def _get_service(self):
		if service_account is None or build is None:
			raise RuntimeError("Google Drive クライアントが利用できません。requirements に google-api-python-client, google-auth を追加してください。")
		
		if "gcp_service_account" not in st.secrets:
			raise RuntimeError("st.secrets['gcp_service_account'] が設定されていません（サービスアカウントJSONを保存してください）。")
		
		info = st.secrets["gcp_service_account"]
		creds = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
		return build("drive", "v3", credentials=creds, cache_discovery=False)
	
	def list_files(self, mime_prefix: str = "image/", modified_after: Optional[str] = None, page_size: int = 1000) -> List[Dict]:
		"""
		指定フォルダ配下のファイルを列挙（デフォルト画像のみ）
		"""
		service = self._get_service()
		
		q = f"'{self.folder_id}' in parents and mimeType contains '{mime_prefix}' and trashed = false"
		if modified_after:
			# RFC3339 形式
			q += f" and modifiedTime > '{modified_after}'"
		
		files: List[Dict] = []
		page_token = None
		while True:
			resp = service.files().list(
				q=q,
				spaces="drive",
				fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
				pageSize=page_size,
				orderBy="modifiedTime desc",
				pageToken=page_token,
			).execute()
			files.extend(resp.get("files", []))
			page_token = resp.get("nextPageToken")
			if not page_token:
				break
		return files
	
	def download_file(self, file_id: str, filename: str) -> Path:
		"""ファイルを download_dir に保存"""
		service = self._get_service()
		request = service.files().get_media(fileId=file_id)
		fh = io.BytesIO()
		downloader = MediaIoBaseDownload(fh, request)
		done = False
		while not done:
			_, done = downloader.next_chunk()
		
		fh.seek(0)
		target = self.download_dir / filename
		with open(target, "wb") as f:
			f.write(fh.read())
		return target
	
	def sync_new_photos(self, modified_after_iso: Optional[str] = None) -> Dict[str, any]:
		"""
		新しい写真をダウンロード
		
		Args:
			modified_after_iso: ISO8601 文字列（これ以降の更新のみ取得）
		Returns:
			{ 'downloaded': int, 'paths': List[Path], 'latest': str }
		"""
		files = self.list_files(mime_prefix="image/", modified_after=modified_after_iso)
		paths: List[Path] = []
		for f in reversed(files):  # 古い順に保存
			try:
				p = self.download_file(f["id"], f["name"])
				paths.append(p)
			except Exception:
				continue
		
		latest = None
		if files:
			latest = files[0].get("modifiedTime")
		return {"downloaded": len(paths), "paths": paths, "latest": latest}



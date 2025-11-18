# 🗺️ JourneyMap

写真とマップを融合した思い出管理アプリ

![JourneyMap Logo](docs/images/logo.png)

## 📖 概要

JourneyMap は、写真や動画の EXIF 情報（GPS座標・撮影日時）を自動抽出し、インタラクティブなマップ上に表示する次世代フォトアルバムアプリです。

### ✨ 主な機能

- 📂 **フォルダスキャン**: 写真・動画を自動的にスキャン
- 🗺️ **インタラクティブマップ**: 撮影地点をマップ上に表示
- 📍 **マーカー＋ルート**: 撮影地点にマーカーを配置し、時系列順にルートを描画
- 📅 **タイムラインフィルタ**: 日付範囲で絞り込み表示
- 📸 **写真一覧**: サムネイル表示、拡大表示、スライドショー
- 🎬 **動画サポート**: サムネイル自動生成、動画再生
- ⚡ **高速処理**: キャッシュ機能による高速読み込み

---

## 🚀 クイックスタート

### 必要な環境

- Python 3.11 以上
- pip（パッケージ管理）

### インストール

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/yourusername/journeymap.git
   cd journeymap
   ```

2. 仮想環境を作成:
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # macOS/Linux
   source venv/bin/activate
   ```

3. 依存ライブラリをインストール:
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

### 起動方法

```bash
streamlit run main.py
```

ブラウザで `http://localhost:8501` にアクセスしてください。

---

## 📚 使い方

### 1. 写真フォルダを選択

サイドバーの「📂 写真フォルダ選択」から、写真が保存されているフォルダのパスを入力してください。

```
例: C:\Users\YourName\Pictures
```

### 2. スキャン開始

「🔍 スキャン開始」ボタンをクリックして、フォルダ内の写真・動画をスキャンします。

### 3. マップを生成

スキャン完了後、「🗺️ マップを生成」ボタンをクリックすると、撮影地点がマップ上に表示されます。

### 4. フィルタリング

「📅 タイムラインフィルタ」で日付範囲を選択し、「🔍 フィルタを適用」をクリックすると、選択した期間の写真のみが表示されます。

### 5. 写真を閲覧

マップ下部の「📸 写真一覧」で、写真をサムネイル表示・拡大表示・スライドショーで楽しめます。

---

## 🎯 対応フォーマット

### 画像
- JPG / JPEG
- PNG
- HEIC

### 動画
- MP4
- MOV

※ GPS 情報を含むファイルのみが地図上に表示されます。

---

## 📁 プロジェクト構造

```
journeymap/
├── main.py                 # メインアプリケーション
├── requirements.txt        # 依存ライブラリ
├── README.md              # プロジェクト説明
├── docs/                  # ドキュメント
│   ├── USER_GUIDE.md      # ユーザーガイド
│   └── DEVELOPER.md       # 開発者ガイド
├── src/                   # ソースコード
│   ├── exif_extractor.py  # EXIF抽出
│   ├── video_metadata.py  # 動画メタデータ
│   ├── video_thumbnail.py # 動画サムネイル
│   ├── database.py        # データベース操作
│   ├── map_generator.py   # マップ生成
│   └── logger.py          # ログ機能
├── data/                  # データ保存先
│   ├── journeymap.db      # SQLiteデータベース
│   └── logs/              # ログファイル
└── tests/                 # テストコード
    ├── test_exif.py
    └── test_database.py
```

---

## 🛠️ 技術スタック

| カテゴリ | 技術 |
|---------|-----|
| UI | Streamlit |
| マップ | Folium (Leaflet.js) |
| 画像処理 | Pillow, exifread |
| 動画処理 | OpenCV |
| データベース | SQLite3 |
| 言語 | Python 3.11+ |

---

## 🤝 コントリビューション

コントリビューションを歓迎します！

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

詳細は [DEVELOPER.md](docs/DEVELOPER.md) を参照してください。

---

## 📄 ライセンス

MIT License - 詳細は [LICENSE](LICENSE) ファイルを参照してください。

---

## 📞 サポート

- 📧 Email: your.email@example.com
- 🐛 Issue: [GitHub Issues](https://github.com/yourusername/journeymap/issues)
- 📖 ドキュメント: [User Guide](docs/USER_GUIDE.md)

---

## 🎉 謝辞

このプロジェクトは以下のオープンソースライブラリを使用しています:

- [Streamlit](https://streamlit.io/)
- [Folium](https://python-visualization.github.io/folium/)
- [Pillow](https://python-pillow.org/)
- [OpenCV](https://opencv.org/)

---

**良い旅を。そして、良い思い出を。** 🗺️📸

# JourneyMap

写真とマップを融合した思い出管理アプリ

## 概要

JourneyMapは、写真や動画のEXIF情報（GPS座標・日時）を自動抽出し、インタラクティブな地図上に可視化するアプリケーションです。

## 機能（MVP版）

- 📂 写真・動画フォルダのスキャン
- 🗺️ 地図上にピン表示
- 🚶 移動ルートの可視化（時系列）
- 📅 タイムラインフィルタ
- 🖼️ 写真・動画ビューア

## 技術スタック

- **言語**: Python 3.11+
- **UI**: Streamlit
- **地図**: Folium
- **DB**: SQLite

## セットアップ（開発中）

```bash
# 仮想環境作成
python -m venv venv

# 仮想環境アクティベート（Windows）
venv\Scripts\activate

# 仮想環境アクティベート（macOS/Linux）
source venv/bin/activate

# 依存ライブラリインストール（Phase 1-2で実装）
pip install -r requirements.txt
```

## 開発状況

- [x] Phase 1-1: プロジェクト構造作成
- [ ] Phase 1-2: 依存ライブラリ設定
- [ ] Phase 1-3: データベース設計
- [ ] Phase 2: データ収集パイプライン
- [ ] Phase 3: マップ生成エンジン
- [ ] Phase 4: Streamlit UI統合
- [ ] Phase 5: インタラクション機能
- [ ] Phase 6: 仕上げ・最適化

## ライセンス

MIT License

## 作成者

開発者名（後で追加）


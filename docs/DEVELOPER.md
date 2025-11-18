# 🛠️ JourneyMap 開発者ガイド

---

## 目次

1. [開発環境のセットアップ](#開発環境のセットアップ)
2. [プロジェクト構造](#プロジェクト構造)
3. [コーディング規約](#コーディング規約)
4. [テスト](#テスト)
5. [デバッグ](#デバッグ)
6. [コントリビューション](#コントリビューション)

---

## 開発環境のセットアップ

### 必要なツール

- Python 3.11+
- Git
- Visual Studio Code（推奨）

### セットアップ手順

1. リポジトリをクローン:
   ```bash
   git clone https://github.com/yourusername/journeymap.git
   cd journeymap
   ```

2. 仮想環境を作成:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

3. 依存ライブラリをインストール:
   ```bash
   pip install -r requirements.txt --break-system-packages
   ```

4. 開発用ライブラリをインストール:
   ```bash
   pip install pytest black flake8 mypy --break-system-packages
   ```

---

## プロジェクト構造

```
journeymap/
├── main.py                 # Streamlitアプリのエントリーポイント
├── src/                    # コアモジュール
│   ├── exif_extractor.py   # EXIF情報抽出
│   ├── video_metadata.py   # 動画メタデータ抽出
│   ├── video_thumbnail.py  # 動画サムネイル生成
│   ├── database.py         # SQLite操作
│   ├── map_generator.py    # Foliumマップ生成
│   └── logger.py           # ロギング機能
├── tests/                  # テストコード
│   ├── test_exif.py
│   ├── test_database.py
│   └── test_map_generator.py
├── data/                   # データ保存先
│   ├── journeymap.db       # SQLiteデータベース
│   └── logs/               # ログファイル
└── docs/                   # ドキュメント
```

---

## コーディング規約

### PEP 8 準拠

Python の標準的なコーディング規約に従います。

### フォーマット

Black を使用して自動フォーマット:

```bash
black src/ tests/
```

### リンティング

Flake8 でコードチェック:

```bash
flake8 src/ tests/ --max-line-length=100
```

### 型ヒント

可能な限り型ヒントを使用:

```python
def extract_exif(image_path: Path) -> Optional[Dict[str, Any]]:
    ...
```

---

## テスト

### テストの実行

```bash
pytest tests/ -v
```

### カバレッジ測定

```bash
pytest --cov=src tests/
```

### テストの書き方

```python
import pytest
from pathlib import Path
from src.exif_extractor import ExifExtractor

def test_extract_exif_valid_image():
    \"\"\"GPS情報を含む画像のテスト\"\"\"
    image_path = Path(\"tests/fixtures/sample_with_gps.jpg\")
    result = ExifExtractor.extract_exif(image_path)
    
    assert result is not None
    assert 'latitude' in result
    assert 'longitude' in result
    assert isinstance(result['latitude'], float)
```

---

## デバッグ

### ログの確認

ログファイルは `data/logs/journeymap_YYYYMMDD.log` に保存されます。

### Streamlit のデバッグモード

```bash
streamlit run main.py --logger.level=debug
```

### Python デバッガ

```python
import pdb; pdb.set_trace()
```

---

## コントリビューション

### ブランチ戦略

- `main`: 本番環境
- `develop`: 開発環境
- `feature/xxx`: 新機能
- `fix/xxx`: バグ修正

### プルリクエストの手順

1. Issue を作成
2. フィーチャーブランチを作成
3. 変更を実装
4. テストを追加
5. PR を作成

### コミットメッセージ

```
feat: 新機能追加
fix: バグ修正
docs: ドキュメント更新
test: テスト追加
refactor: リファクタリング
```

---

**Happy Coding!** 💻



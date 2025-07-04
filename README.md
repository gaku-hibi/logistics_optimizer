# 物流共同配送最適化システム

複数荷主の商品を効率的に配送するための最適化システムです。2Dビンパッキングアルゴリズムと経路最適化により、トラックの使用台数を最小化し、配送効率を向上させます。

## 主な機能

- **商品管理**: サイズ、重量、配送先、期限等の管理
- **トラック管理**: 荷台サイズ、積載量等の管理
- **CSVインポート**: 商品・トラック情報の一括取り込み
- **2Dビンパッキング最適化**: First Fit Decreasingアルゴリズムによる効率的な積載
- **配送ルート最適化**: Nearest Neighbor法による最短経路探索
- **配送スケジュール計算**: 移動時間と作業時間を考慮した到着時刻推定
- **結果の可視化**: 積載配置と配送ルートの視覚的表示

## システム要件

- Docker
- Docker Compose

## セットアップ（Docker使用）

1. リポジトリをクローン:
```bash
git clone <repository-url>
cd logistics_optimizer
```

2. Docker Composeでシステムを起動:
```bash
docker-compose up --build
```

3. ブラウザでアクセス:
```
http://localhost:8000
```

## セットアップ（ローカル環境）

1. Python仮想環境を作成:
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. 依存関係をインストール:
```bash
pip install -r requirements.txt
```

3. データベースをマイグレート:
```bash
python manage.py migrate
```

4. スーパーユーザーを作成:
```bash
python manage.py create_superuser
```

5. サンプルデータをロード:
```bash
python manage.py loaddata fixtures/sample_data.json
```

6. サーバーを起動:
```bash
python manage.py runserver
```

## 使用方法

1. **管理画面へのアクセス**
   - URL: http://localhost:8000/admin/
   - ユーザー名: admin
   - パスワード: admin123

2. **商品・トラックの登録**
   - 管理画面または各一覧画面から新規登録
   - CSVファイルによる一括取り込みも可能

3. **CSVファイルの取り込み**
   - 商品一覧・トラック一覧画面の「CSV取り込み」ボタンをクリック
   - サンプルCSVファイル: `sample_csv/` ディレクトリを参照

4. **配送最適化の実行**
   - 「配送最適化」メニューから実行
   - 発送日時と倉庫住所を指定
   - 最適化結果が表示される

## サンプルデータ

システムには以下のサンプルデータが含まれています：

- 荷主: 3社
- トラック: 3台（異なるサイズ）
- 商品: 8個（異なるサイズ・配送先）

## CSVファイル形式

### 商品CSV（products_sample.csv）
```csv
shipper_name,name,width,height,depth,weight,destination_address,delivery_deadline
株式会社ABC商事,電子機器D,70,45,90,60,東京都新宿区歌舞伎町1-1-1,2025-07-10 17:00
```

必須カラム:
- `shipper_name`: 荷主名
- `name`: 商品名
- `width`: 幅(cm)
- `height`: 高さ(cm)
- `depth`: 奥行き(cm)
- `weight`: 重量(kg)
- `destination_address`: 配送先住所
- `delivery_deadline`: 配送期限 (YYYY-MM-DD HH:MM)

### トラックCSV（trucks_sample.csv）
```csv
name,bed_width,bed_depth,max_weight
トラック4号,280,520,2500
```

必須カラム:
- `name`: トラック名/番号
- `bed_width`: 荷台幅(cm)
- `bed_depth`: 荷台奥行き(cm)
- `max_weight`: 最大積載量(kg)

## 技術仕様

- **バックエンド**: Django 4.2.7
- **データベース**: PostgreSQL
- **フロントエンド**: Bootstrap 5
- **最適化アルゴリズム**:
  - 2Dビンパッキング: First Fit Decreasing
  - 経路最適化: Nearest Neighbor

## 制約事項

- 段積み（商品の上に商品を載せる）は禁止
- 配送は期限日の同日中に完了する必要がある
- 各トラックの最大積載量を超えない
- 複数荷主の共同配送が可能

## トラブルシューティング

### ジオコーディングエラーが発生する場合
- インターネット接続を確認
- Nominatim APIのレート制限に注意（1秒間隔でリクエスト）

### 商品が割り当てられない場合
- トラックの荷台サイズと積載量を確認
- 商品のサイズがトラックに収まるか確認

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。
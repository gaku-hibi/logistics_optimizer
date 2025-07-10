# 物流共同配送最適化システム

パレタイズ、2Dビンパッキング、配送ルート最適化を組み合わせた物流配送最適化システムです。

## 機能

### 主要機能
1. **パレタイズ設計**: 商品のパレット積み上げ設計（積み上げ高さ1.5m固定）
2. **パレタイズ設計ビュー**: パレタイズ設計明細表示および荷姿の3D表示
3. **トラック積載設計**: トラックへの商品（パレット、バラ積み）の積載設計
4. **トラック積載設計ビュー**: 積載明細表示および荷台上の積載状況の2D表示
5. **配送計画**: 配送ルート最適化、配送スケジュール計算
6. **配送計画ビュー**: 配送計画の詳細表示
7. **レポート出力**: パレタイズ設計、トラック積載設計、配送計画のPDF出力
8. **データ入力**: Web画面での直接入力、CSVファイル取り込み対応

### 最適化アルゴリズム
- **パレタイズ**: First Fit Decreasing
- **2Dビンパッキング**: Bottom-Left Fill
- **配送ルート**: Nearest Neighbor

## 技術構成

- **バックエンド**: Python Django 4.2
- **データベース**: PostgreSQL
- **フロントエンド**: HTML5, Bootstrap 5, JavaScript
- **PDF生成**: ReportLab
- **可視化**: Plotly.js
- **コンテナ**: Docker & Docker Compose

## セットアップ

### 1. リポジトリのクローン
```bash
git clone <repository-url>
cd logistics_optimization
```

### 2. 環境変数の設定
```bash
cp .env.example .env
# .envファイルを編集（必要に応じて）
```

### 3. Dockerでの起動
```bash
docker-compose up --build
```

### 4. データベースの初期化
```bash
# マイグレーション実行
docker-compose exec web python manage.py migrate

# 管理者ユーザー作成
docker-compose exec web python manage.py createsuperuser

# サンプルデータ投入（拡充版）
docker-compose exec web python manage.py load_sample_data --clear
```

### 5. アクセス
- アプリケーション: http://localhost:8000
- 管理画面: http://localhost:8000/admin

## 使用方法

### 1. 基本データの登録
1. 管理画面または画面から以下を登録：
   - 商品マスタ（サイズ、重量情報）
   - 荷主情報
   - 配送先情報（住所、緯度経度）
   - トラック情報（荷台サイズ、積載量）

### 2. 出荷依頼の作成
1. 「出荷管理」→「新規出荷依頼」
2. 荷主、配送先、配送期限日を選択
3. 出荷商品と数量を登録

### 3. 配送最適化の実行
1. 「配送計画」→「最適化実行」
2. 対象日を選択
3. 「最適化実行」ボタンをクリック

### 4. 結果の確認
1. 「配送計画」→「配送計画一覧」
2. 作成された計画を確認
3. 詳細画面で2D積載図、配送ルートを表示
4. PDFレポートをダウンロード

## 最新の機能追加 (v2.0)

### マスタ管理機能の強化
- **完全CRUD操作**: すべてのマスタ（商品、荷主、配送先、トラック）で作成・参照・更新・削除が可能
- **詳細画面**: 各マスタの詳細情報と関連データの表示
- **安全削除**: 関連データの警告表示と削除確認機能
- **検索機能**: 商品一覧での検索とページネーション

### PDF出力の日本語対応
- **フォント対応**: Noto Sans CJK フォントによる完全な日本語表示
- **自動フォント検出**: 環境に応じた最適なフォントの自動選択
- **レイアウト改善**: 日本語文書に適したPDFレイアウト

### 大幅拡充されたサンプルデータ
- **商品**: 53種類（PC・電子機器、家電、書籍、生活用品、衣類、食品、梱包材等）
- **荷主**: 10社（多様な業界）
- **配送先**: 23箇所（東京23区、神奈川、埼玉、千葉）
- **出荷依頼**: 150件（14日間、現実的な数量設定）

### サンプルデータ管理コマンド
```bash
# 既存データクリア + 新規サンプルデータ投入
docker-compose exec web python manage.py load_sample_data --clear

# システムフォント確認
docker-compose exec web python manage.py check_fonts
```

### マスタ管理画面の改善
各マスタ一覧画面に以下を追加：
- **新規登録ボタン**: 「+新規登録」でデータ追加
- **編集ボタン**: 各レコードの編集機能
- **削除ボタン**: 安全削除（関連データ警告付き）
- **詳細リンク**: 名前クリックで詳細画面へ

## データ構造

### 主要テーブル
- **Items**: 商品マスタ
- **Shippers**: 荷主マスタ
- **Destinations**: 配送先マスタ
- **Trucks**: トラックマスタ
- **ShippingOrders**: 出荷依頼
- **OrderItems**: 出荷商品
- **DeliveryPlans**: 配送計画
- **PlanOrderDetails**: 配送計画明細
- **PlanItemLoads**: 積載商品

## 最適化ルール

### パレタイズ条件
- 標準パレットサイズ: 110cm × 110cm
- 積み上げ高さ上限: 150cm
- パレット段積み: 禁止
- サイズ超過商品: バラ積み

### 配送制約
- 同一市区町村内での巡回のみ
- 東京23区は1つの配送エリア
- トラック数最小化を目標
- 共同配送（複数荷主の荷物混載）対応

## 開発

### ローカル環境での開発
```bash
# 仮想環境作成
python -m venv venv
source venv/bin/activate  # Windows: venv\\Scripts\\activate

# 依存関係インストール
pip install -r requirements.txt

# 開発サーバー起動
python manage.py runserver
```

### テストの実行
```bash
python manage.py test
```

### データベースのリセット
```bash
docker-compose down -v
docker-compose up --build
```

### Docker再ビルド（フォント更新後）
```bash
# フォント設定を含むDocker再ビルド
docker-compose down
docker-compose up --build
```

## カスタマイズ

### 新しい最適化アルゴリズムの追加
1. `delivery/optimization.py`に新しいクラスを追加
2. `DeliveryOptimizer`クラスで使用するように修正
3. 必要に応じてパラメータ調整用の設定画面を追加

### 新しいレポート形式の追加
1. `delivery/reports.py`に新しい関数を追加
2. `views.py`に対応するビューを追加
3. テンプレートに出力ボタンを追加

## トラブルシューティング

### よくある問題と解決方法

#### PDF文字化け問題
**症状**: PDFファイルで日本語が正しく表示されない
**解決方法**:
1. Dockerを再ビルドしてフォントを更新
```bash
docker-compose down
docker-compose up --build
```
2. フォント確認コマンドで利用可能フォントをチェック
```bash
docker-compose exec web python manage.py check_fonts
```

#### データベース接続エラー
**症状**: "FATAL: database 'logistics_user' does not exist"
**解決方法**:
1. `.env`ファイルの設定を確認
2. データベースコンテナを含めて再起動
```bash
docker-compose down -v
docker-compose up --build
```

#### マイグレーションエラー
**症状**: "Cannot resolve keyword 'deliveryplan' into field"
**解決方法**:
1. 最新のマイグレーションファイルを確認
2. データベースをリセット
```bash
docker-compose down -v
docker-compose up --build
docker-compose exec web python manage.py migrate
```

#### サンプルデータ投入エラー
**症状**: 重複データエラーまたは不整合エラー
**解決方法**:
```bash
# 既存データをクリアして再投入
docker-compose exec web python manage.py load_sample_data --clear
```

### パフォーマンス最適化

#### 大量データでの動作が遅い場合
1. データベースインデックスの確認
2. 最適化アルゴリズムのパラメータ調整
3. サンプルデータ数の調整（load_sample_data.pyの件数変更）

#### メモリ不足エラー
1. Dockerのメモリ制限を増加
2. バッチサイズの調整
3. 配送計画の分割実行

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## サポート

問題や質問がある場合は、GitHubのIssuesをご利用ください。
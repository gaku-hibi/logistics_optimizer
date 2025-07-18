# 配送計画削除機能

## 概要
配送計画を削除する機能を追加しました。

## 実装内容

### 1. ビュー関数の追加
- `delivery/views.py` に `plan_delete` 関数を追加
- 削除確認画面と削除実行処理を実装

### 2. URL設定の追加
- `delivery/urls.py` に削除用のURLパターンを追加
- URL: `/plans/<int:pk>/delete/`

### 3. テンプレートの追加
- `templates/delivery/plan_confirm_delete.html` を作成
- 削除確認画面のテンプレート

### 4. UI の更新
- `templates/delivery/plan_detail.html` - 詳細画面に削除ボタンを追加
- `templates/delivery/plan_list.html` - 一覧画面に削除ボタンを追加

## 機能の動作

### 削除処理の流れ
1. 配送計画一覧または詳細画面で削除ボタンをクリック
2. 削除確認画面が表示される
3. 削除を実行すると、関連データが以下の順序で削除される：
   - `PlanItemLoad` (積載商品データ)
   - `PlanOrderDetail` (配送計画明細)
   - `DeliveryPlan` (配送計画本体)

### 削除時の影響
- 削除された配送計画に関連する出荷依頼は、未配送状態に戻ります
- 関連する出荷依頼、商品、トラックデータは削除されません（PROTECT制約）

### 安全性
- 削除前に確認画面が表示されます
- 関連する出荷依頼の件数が表示されます
- 削除処理でエラーが発生した場合、適切なエラーメッセージが表示されます

## 使用方法

### 配送計画一覧画面から削除
1. 配送計画一覧画面にアクセス
2. 削除したい計画の行の操作列で削除ボタン（🗑️）をクリック
3. 削除確認画面で「削除実行」ボタンをクリック

### 配送計画詳細画面から削除
1. 配送計画詳細画面にアクセス
2. 右サイドバーの操作ボタン部分で「削除」ボタンをクリック
3. 削除確認画面で「削除実行」ボタンをクリック

## データベース設計における考慮事項

### カスケード削除の設定
- `PlanOrderDetail.plan` → `on_delete=models.CASCADE`
- `PlanItemLoad.plan` → `on_delete=models.CASCADE`

### 保護制約の設定
- `PlanOrderDetail.shipping_order` → `on_delete=models.PROTECT`
- `PlanItemLoad.shipping_order` → `on_delete=models.PROTECT`
- `PlanItemLoad.item` → `on_delete=models.PROTECT`
- `DeliveryPlan.truck` → `on_delete=models.PROTECT`

これにより、配送計画の削除時に関連データは適切に削除されますが、参照されているマスタデータ（出荷依頼、商品、トラック）は保護されます。
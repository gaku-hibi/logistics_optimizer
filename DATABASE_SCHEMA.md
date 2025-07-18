# 物流共同配送最適化システム - データベーステーブル設計

## 概要
このドキュメントは物流共同配送最適化システムのデータベーステーブル設計を記載しています。

## テーブル一覧

### 1. 製品テーブル (Items)
出荷する製品のマスタデータ

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| item_code | VARCHAR(100) | ✔ | ✔ | | 品目コード |
| name | VARCHAR(100) | | ✔ | | 製品名 |
| width | INT | | | NULL | 幅(cm) |
| depth | INT | | | NULL | 奥行(cm) |
| height | INT | | | NULL | 高さ(cm) |
| weight | FLOAT | | | NULL | 質量(kg) |
| parts_count | INT | | ✔ | 1 | セット品PCS数 |

- セット品となる場合は、width, depth, heightはNullとなる
- バリデーション: 数値項目は0以上、parts_countは1以上

### 2. セット品(部品)テーブル (Parts)
製品を構成する部品マスタ

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| item_id | VARCHAR(100) | | ✔ | | 品目コード（外部キー） |
| parts_code | VARCHAR(100) | | ✔ | | 部品コード |
| width | INT | | ✔ | | 幅(cm) |
| depth | INT | | ✔ | | 奥行(cm) |
| height | INT | | ✔ | | 高さ(cm) |
| weight | FLOAT | | ✔ | | 質量(kg) |

- 製品が複数の部品から成り立つ場合のみレコードが存在
- 一意制約: (item_id, parts_code)

### 3. 荷主テーブル (Shippers)
荷主（商品の発送元）情報

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | 荷主ID |
| shipper_code | VARCHAR(100) | | ✔ | | 荷主コード |
| name | VARCHAR(200) | | ✔ | | 荷主名 |
| address | VARCHAR(500) | | ✔ | | 住所 |
| contact_phone | VARCHAR(20) | | | | 連絡先電話 |
| contact_email | VARCHAR(100) | | | | 連絡先メール |

- 一意制約: shipper_code

### 4. 配送先テーブル (Destinations)
配送先情報

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | 配送先ID |
| name | VARCHAR(200) | | ✔ | | 配送先名 |
| address | VARCHAR(500) | | ✔ | | 住所（町丁目まで） |
| postal_code | VARCHAR(10) | | | | 郵便番号 |
| latitude | DECIMAL(9,6) | | | | 緯度 |
| longitude | DECIMAL(9,6) | | | | 経度 |
| contact_phone | VARCHAR(20) | | | | 連絡先電話 |

### 5. 出荷依頼テーブル (ShippingOrders)
出荷依頼情報

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | 出荷依頼ID |
| order_number | VARCHAR(100) | | ✔ | | 出荷依頼番号 |
| shipper_id | BIGINT | | ✔ | | 荷主ID（外部キー） |
| destination_id | BIGINT | | ✔ | | 配送先ID（外部キー） |
| delivery_deadline | DATE | | ✔ | | お届け日 |
| created_at | DATETIME | | ✔ | | 作成日時 |
| updated_at | DATETIME | | ✔ | | 更新日時 |

- 一意制約: order_number

### 6. 出荷商品テーブル (OrderItems)
出荷する商品リスト

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| item_id | VARCHAR(100) | | ✔ | | 品目コード（外部キー） |
| quantity | INT | | ✔ | 1 | 数量 |

- 同一品目の商品を複数出荷する場合は、数量で管理

### 7. トラックテーブル (Trucks)
配送用に選定可能なトラック

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| width | INT | | ✔ | 0 | 荷台幅(cm) |
| depth | INT | | ✔ | 0 | 荷台奥行(cm) |
| height | INT | | ✔ | 0 | 荷台高さ(cm) |
| payload | INT | | ✔ | 0 | 最大積載量(kg) |
| shipping_company | VARCHAR(256) | | | | 運送会社名 |
| truck_class | VARCHAR(100) | | | | 車格(4t等) |
| model | VARCHAR(100) | | | | 車種 |

### 8. 配送計画テーブル (DeliveryPlans)
出荷依頼を元に作成される配送計画

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | 配送計画ID |
| plan_date | DATE | | ✔ | | 配送日 |
| truck_id | BIGINT | | ✔ | | 使用するトラックID（外部キー） |
| departure_time | DATETIME | | ✔ | | 出発予定時刻 |
| total_weight | FLOAT | | ✔ | | 積載合計重量(kg) |
| total_volume | INT | | ✔ | | 積載合計体積(cm³) |
| route_distance_km | FLOAT | | | | 想定走行距離(km) |
| created_at | DATETIME | | ✔ | | 作成日時 |

### 9. 配送計画明細テーブル (PlanOrderDetails)
配送計画と出荷依頼の関連（多対多を解消）

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| delivery_sequence | INT | | ✔ | | 配送順序 |
| estimated_arrival | DATETIME | | ✔ | | 到着予定時刻 |
| travel_time_minutes | INT | | ✔ | | 移動時間(分) |

- 一意制約: (plan_id, shipping_order_id)

### 10. 積載商品テーブル (PlanItemLoads) **[旧システム - 後方互換性のため保持]**
トラックに積む各商品の詳細と配置位置

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| item_id | VARCHAR(100) | | ✔ | | 品目コード（外部キー） |
| quantity | INT | | ✔ | | 個数 |
| position_x | INT | | ✔ | | 積載位置X座標(cm) |
| position_y | INT | | ✔ | | 積載位置Y座標(cm) |
| rotation | INT | | ✔ | 0 | 回転角度(0,90,180,270) |

**注意**: このテーブルは後方互換性のため保持されていますが、新システムでは LoadPallet テーブルを使用します。

### 11. パレタイズ設計テーブル (PalletizePlans)
パレタイズ設計結果の管理

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| delivery_date | DATE | | ✔ | | 配送日 |
| total_items | INT | | ✔ | | 総商品数 |
| total_pallets | INT | | ✔ | | パレット数 |
| total_loose_items | INT | | ✔ | | バラ積み商品数 |
| created_at | DATETIME | | ✔ | | 作成日時 |

### 12. パレット詳細テーブル (PalletDetails)
各パレットの詳細情報

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| palletize_plan_id | BIGINT | | ✔ | | パレタイズ設計ID（外部キー） |
| pallet_number | INT | | ✔ | | パレット番号 |
| total_weight | FLOAT | | ✔ | | 総重量(kg) |
| total_volume | INT | | ✔ | | 総体積(cm³) |
| utilization | FLOAT | | ✔ | | 積載率(%) |

- 一意制約: (palletize_plan_id, pallet_number)

### 13. パレット積載商品テーブル (PalletItems)
パレットに積載される商品の詳細

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| pallet_id | BIGINT | | ✔ | | パレット詳細ID（外部キー） |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| item_id | VARCHAR(100) | | ✔ | | 品目コード（外部キー） |
| part_id | BIGINT | | | | 部品ID（外部キー） |
| position_x | INT | | ✔ | | X座標(cm) |
| position_y | INT | | ✔ | | Y座標(cm) |
| position_z | INT | | ✔ | | Z座標(cm) |
| width | INT | | ✔ | | 幅(cm) |
| depth | INT | | ✔ | | 奥行(cm) |
| height | INT | | ✔ | | 高さ(cm) |
| weight | FLOAT | | ✔ | | 重量(kg) |

### 14. バラ積み商品テーブル (LooseItems)
パレタイズできない商品の情報

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| palletize_plan_id | BIGINT | | ✔ | | パレタイズ設計ID（外部キー） |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| item_id | VARCHAR(100) | | ✔ | | 品目コード（外部キー） |
| width | INT | | ✔ | | 幅(cm) |
| depth | INT | | ✔ | | 奥行(cm) |
| height | INT | | ✔ | | 高さ(cm) |
| weight | FLOAT | | ✔ | | 重量(kg) |
| reason | VARCHAR(100) | | ✔ | | 理由 |

### 15. パレット設定テーブル (PalletConfigurations)
パレット設定の管理

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| name | VARCHAR(100) | | ✔ | | 設定名 |
| width | INT | | ✔ | 100 | パレット幅(cm) |
| depth | INT | | ✔ | 100 | パレット奥行(cm) |
| max_height | INT | | ✔ | 80 | 最大積み上げ高さ(cm) |
| max_weight | FLOAT | | ✔ | 100.0 | 最大積載重量(kg) |
| is_default | BOOLEAN | | ✔ | FALSE | デフォルト設定 |
| created_at | DATETIME | | ✔ | | 作成日時 |
| updated_at | DATETIME | | ✔ | | 更新日時 |

- 一意制約: name
- デフォルト設定は1つのみ許可

---

## 新システム: パレット単位積載管理

### 16. 統一パレットテーブル (UnifiedPallets) **[新システム - メイン]**
パレタイズされたパレットと疑似パレットの統一管理

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | パレットID |
| pallet_type | VARCHAR(20) | | ✔ | | パレットタイプ(REAL/VIRTUAL) |
| delivery_date | DATE | | ✔ | | 配送日 |
| width | INT | | ✔ | | パレット幅(cm) |
| depth | INT | | ✔ | | パレット奥行(cm) |
| height | INT | | ✔ | | パレット高さ(cm) |
| weight | FLOAT | | ✔ | | パレット重量(kg) |
| volume | INT | | ✔ | | パレット体積(cm³) |
| shipping_order_id | BIGINT | | ✔ | | 出荷依頼ID（外部キー） |
| pallet_detail_id | BIGINT | | | | パレット詳細ID（外部キー、REALパレットのみ） |
| item_id | VARCHAR(100) | | | | 品目コード（VIRTUALパレットのみ） |
| item_quantity | INT | | | | 商品数量（VIRTUALパレットのみ） |
| created_at | DATETIME | | ✔ | | 作成日時 |

#### パレットタイプ
- **REAL**: パレタイズされた実際のパレット
- **VIRTUAL**: バラ積み商品を疑似パレットとして扱う

#### バリデーション
- REALパレット: pallet_detail_id が必須、item_id と item_quantity は NULL
- VIRTUALパレット: item_id と item_quantity が必須、pallet_detail_id は NULL

### 17. 積載パレットテーブル (LoadPallets) **[新システム - メイン]**
パレット単位での積載管理（旧PlanItemLoadsの置き換え）

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| pallet_id | BIGINT | | ✔ | | 統一パレットID（外部キー） |
| position_x | INT | | ✔ | | 積載位置X座標(cm) |
| position_y | INT | | ✔ | | 積載位置Y座標(cm) |
| rotation | INT | | ✔ | 0 | 回転角度(0,90,180,270) |
| load_sequence | INT | | ✔ | | 積み込み順序 |

### 18. パレット積載履歴テーブル (PalletLoadHistory) **[新システム - メイン]**
パレットの使用状況管理（重複防止）

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| pallet_id | BIGINT | | ✔ | | 統一パレットID（外部キー） |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| allocated_at | DATETIME | | ✔ | | 割り当て日時 |
| status | VARCHAR(20) | | ✔ | ALLOCATED | ステータス |

#### ステータス
- **ALLOCATED**: 割り当て済み
- **USED**: 使用中
- **COMPLETED**: 完了

- 一意制約: (pallet_id, plan_id)

---

## 主要な関連性

### 外部キー制約

#### 基本エンティティ
- Parts.item_id → Items.item_code
- ShippingOrders.shipper_id → Shippers.id
- ShippingOrders.destination_id → Destinations.id
- OrderItems.shipping_order_id → ShippingOrders.id
- OrderItems.item_id → Items.item_code

#### 配送計画
- DeliveryPlans.truck_id → Trucks.id
- PlanOrderDetails.plan_id → DeliveryPlans.id
- PlanOrderDetails.shipping_order_id → ShippingOrders.id

#### 旧システム (後方互換性)
- PlanItemLoads.plan_id → DeliveryPlans.id
- PlanItemLoads.shipping_order_id → ShippingOrders.id
- PlanItemLoads.item_id → Items.item_code

#### パレタイズ設計
- PalletDetails.palletize_plan_id → PalletizePlans.id
- PalletItems.pallet_id → PalletDetails.id
- PalletItems.shipping_order_id → ShippingOrders.id
- PalletItems.item_id → Items.item_code
- PalletItems.part_id → Parts.id
- LooseItems.palletize_plan_id → PalletizePlans.id
- LooseItems.shipping_order_id → ShippingOrders.id
- LooseItems.item_id → Items.item_code

#### 新システム (パレット単位積載)
- UnifiedPallets.shipping_order_id → ShippingOrders.id
- UnifiedPallets.pallet_detail_id → PalletDetails.id (REALパレットのみ)
- UnifiedPallets.item_id → Items.item_code (VIRTUALパレットのみ)
- LoadPallets.plan_id → DeliveryPlans.id
- LoadPallets.pallet_id → UnifiedPallets.id
- PalletLoadHistory.pallet_id → UnifiedPallets.id
- PalletLoadHistory.plan_id → DeliveryPlans.id

### 重要な制約

1. **出荷依頼別パレット分離**: 異なる出荷依頼IDの商品は同一パレットに配置されない
2. **パレット設定**: デフォルト設定は1つのみ許可
3. **配送計画の一意性**: 同一配送計画内で同一出荷依頼は1つのみ
4. **パレット番号の一意性**: 同一パレタイズ設計内でパレット番号は一意
5. **パレット重複防止**: 同一パレットが複数の配送計画に割り当てられることを防止
6. **統一パレットタイプ別制約**: REALパレットとVIRTUALパレットで必須フィールドが異なる

## システムアーキテクチャの変更点

### 従来システム (商品単位積載)
```
ShippingOrders → OrderItems → Items
                     ↓
DeliveryPlans → PlanItemLoads (商品単位で積載管理)
```

### 新システム (パレット単位積載)
```
ShippingOrders → OrderItems → Items
                     ↓
              PalletizePlans
                ↓        ↓
         PalletDetails  LooseItems
                ↓        ↓
           UnifiedPallets (統一パレット管理)
                ↓
DeliveryPlans → LoadPallets (パレット単位で積載管理)
                ↓
         PalletLoadHistory (重複防止)
```

## 機能の実装

- **3D/2Dビンパッキング**: パレタイズ最適化
- **パレット単位積載**: 統一パレットシステム
- **配送ルート最適化**: 最近傍法による経路計算
- **重量・体積制約**: トラック積載制限の管理
- **パレット重複防止**: 履歴管理による重複使用防止
- **3D可視化**: Three.jsによるパレット配置の可視化
- **PDF出力**: 配送計画レポートの生成
- **後方互換性**: 旧システムとの互換性保持

## データ移行戦略

1. **既存データ保持**: 旧システムのテーブルは保持
2. **統一パレット作成**: 既存のPalletDetailsとLooseItemsからUnifiedPalletsを作成
3. **積載パレット作成**: 既存のPlanItemLoadsからLoadPalletsを作成
4. **段階的移行**: 新システムと旧システムの両方をサポート
5. **完全移行後**: 旧システムテーブルの廃止（将来的に）
# 新しいテーブル設計提案 - パレット単位の積載管理

## 設計変更の概要

### 変更の目的
1. **パレット単位の積載管理**: 商品単位ではなく、パレット単位でトラック積載を管理
2. **統一的な積載概念**: パレタイズされた商品も、バラ積み商品も「パレット」として統一管理
3. **最適化の簡素化**: トラック積載最適化をパレット単位で実行

### 新しいテーブル設計

## 1. 積載パレットテーブル (LoadPallets)
**旧 PlanItemLoads テーブルの置き換え**

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| pallet_id | BIGINT | | ✔ | | パレットID（外部キー） |
| position_x | INT | | ✔ | | 積載位置X座標(cm) |
| position_y | INT | | ✔ | | 積載位置Y座標(cm) |
| rotation | INT | | ✔ | 0 | 回転角度(0,90,180,270) |
| load_sequence | INT | | ✔ | | 積み込み順序 |

## 2. 統一パレットテーブル (UnifiedPallets)
**パレタイズされたパレットと疑似パレットの統一管理**

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

### パレットタイプ
- **REAL**: パレタイズされた実際のパレット
- **VIRTUAL**: バラ積み商品を疑似パレットとして扱う

## 3. パレット積載履歴テーブル (PalletLoadHistory)
**パレットの使用状況管理**

| カラム名 | データ型 | 主キー | Not Null | デフォルト値 | 説明 |
|----------|----------|--------|----------|--------------|------|
| id | BIGINT | ✔ | ✔ | autoincrement | ID |
| pallet_id | BIGINT | | ✔ | | パレットID（外部キー） |
| plan_id | BIGINT | | ✔ | | 配送計画ID（外部キー） |
| allocated_at | DATETIME | | ✔ | | 割り当て日時 |
| status | VARCHAR(20) | | ✔ | ALLOCATED | ステータス(ALLOCATED/USED/COMPLETED) |

## 変更による改善点

### 1. 積載管理の統一
- パレタイズされた商品もバラ積み商品も、すべて「パレット」として管理
- トラック積載最適化がパレット単位で実行可能

### 2. パレット重複使用の防止
- `PalletLoadHistory`テーブルでパレットの使用状況を管理
- 同一パレットが複数のトラックに割り当てられることを防止

### 3. 最適化アルゴリズムの簡素化
- 2Dビンパッキングの対象がパレット単位に統一
- 商品レベルの複雑な制約管理が不要

### 4. 現実的な物流管理
- パレット単位での積載は実際の物流現場に即している
- 荷降ろし時の効率性が向上

## 既存データのマイグレーション

### 1. UnifiedPallets テーブルの作成
```sql
-- REALパレットの作成（既存のPalletDetailから）
INSERT INTO UnifiedPallets (
    pallet_type, delivery_date, width, depth, height, weight, volume,
    shipping_order_id, pallet_detail_id, created_at
)
SELECT 
    'REAL',
    pp.delivery_date,
    pc.width,
    pc.depth,
    pd.total_volume / (pc.width * pc.depth) AS height,
    pd.total_weight,
    pd.total_volume,
    pi.shipping_order_id,
    pd.id,
    pd.created_at
FROM PalletDetails pd
JOIN PalletizePlans pp ON pd.palletize_plan_id = pp.id
JOIN PalletItems pi ON pi.pallet_id = pd.id
JOIN PalletConfiguration pc ON pc.is_default = true
GROUP BY pd.id;

-- VIRTUALパレットの作成（既存のLooseItemから）
INSERT INTO UnifiedPallets (
    pallet_type, delivery_date, width, depth, height, weight, volume,
    shipping_order_id, item_id, item_quantity, created_at
)
SELECT 
    'VIRTUAL',
    pp.delivery_date,
    li.width,
    li.depth,
    li.height,
    li.weight,
    li.width * li.depth * li.height,
    li.shipping_order_id,
    li.item_id,
    1,
    li.created_at
FROM LooseItems li
JOIN PalletizePlans pp ON li.palletize_plan_id = pp.id;
```

### 2. LoadPallets テーブルの作成
```sql
-- 既存のPlanItemLoadsから変換
INSERT INTO LoadPallets (
    plan_id, pallet_id, position_x, position_y, rotation, load_sequence
)
SELECT 
    pil.plan_id,
    up.id,
    pil.position_x,
    pil.position_y,
    pil.rotation,
    ROW_NUMBER() OVER (PARTITION BY pil.plan_id ORDER BY pil.id)
FROM PlanItemLoads pil
JOIN UnifiedPallets up ON (
    up.pallet_type = 'VIRTUAL' AND 
    up.item_id = pil.item_id AND 
    up.shipping_order_id = pil.shipping_order_id
);
```

## 新しいアルゴリズムの実装

### 1. パレット最適化
```python
def optimize_pallet_loading(pallets: List[UnifiedPallet], truck: Truck) -> List[LoadPallet]:
    """パレット単位での積載最適化"""
    # 2Dビンパッキングをパレット単位で実行
    # 重量制約とサイズ制約を考慮
    pass
```

### 2. パレット割り当て管理
```python
def allocate_pallets_to_plan(plan: DeliveryPlan, pallets: List[UnifiedPallet]):
    """パレットを配送計画に割り当て"""
    # 使用済みパレットの重複チェック
    # PalletLoadHistoryテーブルの更新
    pass
```

このような設計変更により、より現実的で効率的な物流管理システムが実現できます。
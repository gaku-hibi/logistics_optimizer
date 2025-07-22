#!/usr/bin/env python
"""
最新のパレタイズ設計からUnifiedPalletを再作成するスクリプト
"""

import os
import sys
import django
from datetime import datetime

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import PalletizePlan, UnifiedPallet, PalletConfiguration

def recreate_unified_pallets_from_latest():
    """最新のパレタイズ設計からUnifiedPalletを再作成"""
    
    date = datetime(2025, 7, 20).date()
    
    print(f"=== 7月20日の最新パレタイズ設計からUnifiedPallet再作成 ===\n")
    
    # 既存のUnifiedPalletを削除
    print("既存のUnifiedPalletを削除中...")
    existing_count = UnifiedPallet.objects.filter(delivery_date=date).count()
    UnifiedPallet.objects.filter(delivery_date=date).delete()
    print(f"{existing_count}個のUnifiedPalletを削除しました")
    
    # 最新のパレタイズ設計を取得
    latest_plan = PalletizePlan.objects.filter(delivery_date=date).order_by('-id').first()
    
    if not latest_plan:
        print("パレタイズ設計が見つかりません")
        return
    
    print(f"\n最新のパレタイズ設計: ID={latest_plan.id}")
    print(f"  パレット数: {latest_plan.pallets.count()}")
    print(f"  バラ積み数: {latest_plan.loose_items.count()}")
    
    # パレット設定を取得
    pallet_config = PalletConfiguration.get_default()
    
    created_count = 0
    
    print(f"\nREALパレットの作成開始...")
    
    # REALパレットの作成
    for i, pallet_detail in enumerate(latest_plan.pallets.all(), 1):
        # パレットに含まれる全ての注文を収集
        pallet_orders = []
        for pallet_item in pallet_detail.items.all():
            if pallet_item.shipping_order and pallet_item.shipping_order not in pallet_orders:
                pallet_orders.append(pallet_item.shipping_order)
        
        # 代表的な注文を設定
        representative_order = pallet_orders[0] if pallet_orders else None
        
        # UnifiedPalletを作成
        unified_pallet = UnifiedPallet.objects.create(
            pallet_type='REAL',
            pallet_detail=pallet_detail,
            delivery_date=latest_plan.delivery_date,
            width=pallet_config.width,
            depth=pallet_config.depth,
            height=pallet_config.max_height,
            weight=pallet_detail.total_weight,
            volume=pallet_detail.total_volume,
            shipping_order=representative_order
        )
        
        # related_ordersを設定
        if pallet_orders:
            unified_pallet.related_orders.set(pallet_orders)
        
        created_count += 1
        
        if i <= 5 or i % 20 == 0:  # 最初の5個と20個ごとに表示
            order_ids = [o.id for o in pallet_orders]
            print(f"  REALパレット {i}/80: ID={unified_pallet.id}, 関連注文={order_ids}")
    
    print(f"\nVIRTUALパレット（バラ積み）の作成開始...")
    
    # VIRTUALパレット（バラ積み）の作成
    for i, loose_item in enumerate(latest_plan.loose_items.all(), 1):
        # 体積を計算
        volume = loose_item.width * loose_item.depth * loose_item.height
        
        unified_pallet = UnifiedPallet.objects.create(
            pallet_type='VIRTUAL',
            item=loose_item.item,
            item_quantity=1,  # バラ積み商品の数量は1
            delivery_date=latest_plan.delivery_date,
            width=loose_item.width,
            depth=loose_item.depth,
            height=loose_item.height,
            weight=loose_item.weight,
            volume=volume,
            shipping_order=loose_item.shipping_order
        )
        
        # related_ordersを設定
        unified_pallet.related_orders.set([loose_item.shipping_order])
        
        created_count += 1
        print(f"  VIRTUALパレット {i}: ID={unified_pallet.id}, 商品={loose_item.item.name}, 注文ID={loose_item.shipping_order.id}")
    
    print(f"\n作成完了: {created_count}個のUnifiedPalletを作成しました")
    
    # 結果を確認
    unified_pallets = UnifiedPallet.objects.filter(delivery_date=date)
    real_count = unified_pallets.filter(pallet_type='REAL').count()
    virtual_count = unified_pallets.filter(pallet_type='VIRTUAL').count()
    
    print(f"\n最終結果:")
    print(f"  REALパレット: {real_count}")
    print(f"  VIRTUALパレット: {virtual_count}")
    print(f"  合計: {unified_pallets.count()}")
    
    # 注文別の関連パレット数を確認
    print(f"\n注文別のパレット関連数:")
    from collections import defaultdict
    order_pallet_count = defaultdict(int)
    
    for pallet in unified_pallets:
        for order in pallet.related_orders.all():
            order_pallet_count[order.id] += 1
    
    for order_id, count in sorted(order_pallet_count.items()):
        print(f"  注文ID {order_id}: {count}個のパレット")

if __name__ == '__main__':
    recreate_unified_pallets_from_latest()
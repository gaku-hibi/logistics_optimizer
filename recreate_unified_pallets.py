#!/usr/bin/env python
"""
7月20日のパレタイズ設計からUnifiedPalletを再作成するスクリプト
"""

import os
import sys
import django
from datetime import datetime

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import PalletizePlan, UnifiedPallet, PalletConfiguration, ShippingOrder

def recreate_unified_pallets_for_july20():
    """7月20日のUnifiedPalletを再作成"""
    
    date = datetime(2025, 7, 20).date()
    
    print(f"=== 7月20日のUnifiedPallet再作成 ===\n")
    
    # 既存のUnifiedPalletを削除
    print("既存のUnifiedPalletを削除中...")
    existing_count = UnifiedPallet.objects.filter(delivery_date=date).count()
    UnifiedPallet.objects.filter(delivery_date=date).delete()
    print(f"{existing_count}個のUnifiedPalletを削除しました")
    
    # パレタイズ設計を取得
    plans = PalletizePlan.objects.filter(delivery_date=date)
    print(f"\nパレタイズ設計数: {plans.count()}")
    
    if not plans.exists():
        print("パレタイズ設計が見つかりません")
        return
    
    # パレット設定を取得
    pallet_config = PalletConfiguration.get_default()
    
    created_count = 0
    
    for plan in plans:
        print(f"\nパレタイズ設計 ID={plan.id} を処理中...")
        
        # REALパレットの作成
        for pallet_detail in plan.pallets.all():
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
                delivery_date=plan.delivery_date,
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
            print(f"  REALパレット作成: ID={unified_pallet.id}, 関連注文数={len(pallet_orders)}")
        
        # VIRTUALパレット（バラ積み）の作成
        for loose_item in plan.loose_items.all():
            # 体積を計算
            volume = loose_item.width * loose_item.depth * loose_item.height
            
            unified_pallet = UnifiedPallet.objects.create(
                pallet_type='VIRTUAL',
                item=loose_item.item,
                item_quantity=1,  # バラ積み商品の数量は1
                delivery_date=plan.delivery_date,
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
            print(f"  VIRTUALパレット作成: ID={unified_pallet.id}, 商品={loose_item.item.name}")
    
    print(f"\n作成完了: {created_count}個のUnifiedPalletを作成しました")
    
    # 結果を確認
    unified_pallets = UnifiedPallet.objects.filter(delivery_date=date)
    real_count = unified_pallets.filter(pallet_type='REAL').count()
    virtual_count = unified_pallets.filter(pallet_type='VIRTUAL').count()
    
    print(f"\n最終結果:")
    print(f"  REALパレット: {real_count}")
    print(f"  VIRTUALパレット: {virtual_count}")
    print(f"  合計: {unified_pallets.count()}")

if __name__ == '__main__':
    recreate_unified_pallets_for_july20()
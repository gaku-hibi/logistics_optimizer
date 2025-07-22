#!/usr/bin/env python
"""
7月20日のパレタイズ設計とREALパレット作成を詳細調査するスクリプト
"""

import os
import sys
import django
from datetime import datetime

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import PalletizePlan, PalletDetail, PalletItem, UnifiedPallet, ShippingOrder

def debug_palletize_plan():
    """パレタイズ設計とREALパレット作成の詳細調査"""
    
    date = datetime(2025, 7, 20).date()
    
    print(f"=== 7月20日のパレタイズ設計詳細調査 ===\n")
    
    # パレタイズ設計を確認
    plans = PalletizePlan.objects.filter(delivery_date=date)
    print(f"パレタイズ設計数: {plans.count()}")
    
    for plan in plans:
        print(f"\nパレタイズ設計 ID={plan.id}:")
        print(f"  配送日: {plan.delivery_date}")
        print(f"  パレット数: {plan.pallets.count()}")
        print(f"  バラ積み数: {plan.loose_items.count()}")
        
        # パレット詳細を確認
        pallets = plan.pallets.all()[:10]  # 最初の10個
        print(f"\nパレット詳細（最初の10個）:")
        for pallet in pallets:
            print(f"  パレットID={pallet.id}:")
            print(f"    商品数: {pallet.items.count()}")
            print(f"    重量: {pallet.total_weight}kg")
            print(f"    体積: {pallet.total_volume}cm³")
            
            # パレット内の商品を確認
            items = pallet.items.all()[:3]  # 最初の3個
            print(f"    商品（最初の3個）:")
            for item in items:
                print(f"      商品: {item.item.name}, 注文ID: {item.shipping_order.id}")
        
        # バラ積み商品を確認
        loose_items = plan.loose_items.all()[:5]  # 最初の5個
        print(f"\nバラ積み商品（最初の5個）:")
        for loose in loose_items:
            print(f"  商品: {loose.item.name}, 注文ID: {loose.shipping_order.id}")
    
    # UnifiedPalletの状況を確認
    print(f"\n=== UnifiedPallet状況 ===")
    unified_pallets = UnifiedPallet.objects.filter(delivery_date=date)
    real_pallets = unified_pallets.filter(pallet_type='REAL')
    virtual_pallets = unified_pallets.filter(pallet_type='VIRTUAL')
    
    print(f"UnifiedPallet総数: {unified_pallets.count()}")
    print(f"  REALパレット: {real_pallets.count()}")
    print(f"  VIRTUALパレット: {virtual_pallets.count()}")
    
    # REALパレットが存在する場合の詳細
    if real_pallets.exists():
        print(f"\nREALパレット詳細（最初の5個）:")
        for pallet in real_pallets[:5]:
            print(f"  パレットID={pallet.id}:")
            print(f"    パレット詳細ID: {pallet.pallet_detail.id if pallet.pallet_detail else 'None'}")
            print(f"    関連注文数: {pallet.related_orders.count()}")
            if pallet.related_orders.exists():
                order_ids = list(pallet.related_orders.values_list('id', flat=True))
                print(f"    注文ID: {order_ids}")
    else:
        print("\nREALパレットが存在しません！")
        
        # パレタイズ設計のパレットがUnifiedPalletに変換されているかチェック
        print("\nパレタイズ設計のパレットとUnifiedPalletの対応をチェック:")
        for plan in plans:
            for pallet_detail in plan.pallets.all()[:5]:  # 最初の5個
                related_unified = UnifiedPallet.objects.filter(
                    pallet_detail=pallet_detail,
                    delivery_date=date
                )
                print(f"  パレット詳細ID={pallet_detail.id} -> UnifiedPallet: {related_unified.count()}個")
    
    # 配送依頼とパレットの関連を確認
    print(f"\n=== 配送依頼とパレットの関連確認 ===")
    orders = ShippingOrder.objects.filter(delivery_deadline=date)
    
    for order in orders[:10]:  # 最初の10個
        related_pallets = UnifiedPallet.objects.filter(
            delivery_date=date,
            related_orders=order
        )
        pallet_items_count = PalletItem.objects.filter(
            shipping_order=order,
            pallet__palletize_plan__delivery_date=date
        ).count()
        
        print(f"  注文ID={order.id}: UnifiedPallet={related_pallets.count()}個, PalletItem={pallet_items_count}個")

if __name__ == '__main__':
    debug_palletize_plan()
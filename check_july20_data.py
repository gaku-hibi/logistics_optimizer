#!/usr/bin/env python
"""
7月20日のデータを確認するスクリプト
"""

import os
import sys
import django
from datetime import datetime

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import PalletizePlan, UnifiedPallet, ShippingOrder

def check_july20_data():
    """7月20日のデータを確認"""
    
    date = datetime(2025, 7, 20).date()
    
    print(f"=== 7月20日のデータ確認 ===\n")
    
    # 出荷依頼を確認
    orders = ShippingOrder.objects.filter(delivery_deadline=date)
    print(f"出荷依頼数: {orders.count()}")
    for order in orders[:10]:  # 最初の10件
        print(f"  注文ID={order.id}, 番号={order.order_number}, 配送先={order.destination.name}")
    
    # パレタイズ設計を確認
    print(f"\nパレタイズ設計:")
    plans = PalletizePlan.objects.filter(delivery_date=date)
    print(f"パレタイズ設計数: {plans.count()}")
    
    for plan in plans:
        print(f"\nパレタイズ設計 ID={plan.id}:")
        print(f"  パレット数: {plan.pallets.count()}")
        print(f"  バラ積み数: {plan.loose_items.count()}")
        
        # パレット詳細を確認
        if plan.pallets.exists():
            print("  パレット詳細:")
            for pallet in plan.pallets.all()[:5]:  # 最初の5つだけ表示
                print(f"    パレットID={pallet.id}: 商品数={pallet.items.count()}, 重量={pallet.total_weight}kg")
        else:
            print("  ※パレットがありません")
    
    # UnifiedPalletを確認
    print(f"\nUnifiedPallet:")
    unified_pallets = UnifiedPallet.objects.filter(delivery_date=date)
    print(f"UnifiedPallet数: {unified_pallets.count()}")
    
    # タイプ別に集計
    real_count = unified_pallets.filter(pallet_type='REAL').count()
    virtual_count = unified_pallets.filter(pallet_type='VIRTUAL').count()
    print(f"  REALパレット: {real_count}")
    print(f"  VIRTUALパレット: {virtual_count}")
    
    # related_ordersの状態を確認
    print("\nrelated_ordersの状態:")
    empty_related = 0
    for pallet in unified_pallets[:20]:  # 最初の20件
        related_count = pallet.related_orders.count()
        if related_count == 0:
            empty_related += 1
        print(f"  パレットID={pallet.id} (type={pallet.pallet_type}): related_orders数={related_count}")
    
    if empty_related > 0:
        print(f"\n警告: {empty_related}個のパレットでrelated_ordersが空です")

if __name__ == '__main__':
    check_july20_data()
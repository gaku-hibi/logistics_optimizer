#!/usr/bin/env python
"""
7月20日の配送依頼と配送計画を詳細分析するスクリプト
"""

import os
import sys
import django
from datetime import datetime

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import ShippingOrder, DeliveryPlan, PlanOrderDetail, UnifiedPallet

def analyze_july20_plans():
    """7月20日の配送依頼と配送計画を分析"""
    
    date = datetime(2025, 7, 20).date()
    
    print(f"=== 7月20日の配送依頼と配送計画の分析 ===\n")
    
    # 出荷依頼を確認
    orders = ShippingOrder.objects.filter(delivery_deadline=date)
    print(f"配送依頼数: {orders.count()}")
    print("\n配送依頼一覧:")
    for order in orders:
        print(f"  ID={order.id}, 番号={order.order_number}, 荷主={order.shipper.name}, 配送先={order.destination.name}")
    
    # 配送計画を確認
    plans = DeliveryPlan.objects.filter(plan_date=date)
    print(f"\n配送計画数: {plans.count()}")
    
    # 配送計画に含まれる配送依頼を確認
    covered_order_ids = set()
    
    print("\n配送計画詳細:")
    for i, plan in enumerate(plans, 1):
        print(f"\n配送計画 {i} (ID={plan.id}):")
        print(f"  トラック: {plan.truck.id} ({plan.truck.width}x{plan.truck.depth}cm, {plan.truck.payload}kg)")
        print(f"  出発時刻: {plan.departure_time}")
        print(f"  総重量: {plan.total_weight}kg, 総体積: {plan.total_volume}cm³")
        
        # この計画の配送依頼詳細
        plan_details = PlanOrderDetail.objects.filter(plan=plan).order_by('delivery_sequence')
        print(f"  配送依頼数: {plan_details.count()}")
        
        for detail in plan_details:
            covered_order_ids.add(detail.shipping_order.id)
            print(f"    順序{detail.delivery_sequence}: 注文ID={detail.shipping_order.id}, "
                  f"番号={detail.shipping_order.order_number}, "
                  f"配送先={detail.shipping_order.destination.name}, "
                  f"到着予定={detail.estimated_arrival}")
    
    # 未処理の配送依頼を特定
    all_order_ids = set(orders.values_list('id', flat=True))
    uncovered_order_ids = all_order_ids - covered_order_ids
    
    print(f"\n=== 処理状況サマリ ===")
    print(f"全配送依頼数: {len(all_order_ids)}")
    print(f"処理済み配送依頼数: {len(covered_order_ids)}")
    print(f"未処理配送依頼数: {len(uncovered_order_ids)}")
    
    if uncovered_order_ids:
        print(f"\n未処理の配送依頼:")
        uncovered_orders = orders.filter(id__in=uncovered_order_ids)
        for order in uncovered_orders:
            print(f"  ID={order.id}, 番号={order.order_number}, 荷主={order.shipper.name}, 配送先={order.destination.name}")
            
            # この配送依頼に関連するUnifiedPalletを確認
            related_pallets = UnifiedPallet.objects.filter(
                delivery_date=date,
                related_orders=order
            )
            print(f"    関連パレット数: {related_pallets.count()}")
            for pallet in related_pallets[:3]:  # 最初の3つだけ表示
                print(f"      パレットID={pallet.id}, type={pallet.pallet_type}, "
                      f"サイズ={pallet.width}x{pallet.depth}x{pallet.height}cm, 重量={pallet.weight}kg")
    else:
        print("全ての配送依頼が処理されています。")
    
    # 地域別分析
    print(f"\n=== 地域別分析 ===")
    from collections import defaultdict
    
    region_orders = defaultdict(list)
    for order in orders:
        # 簡易的に地域を判定（実際のロジックに合わせて調整）
        address = order.destination.address
        if '東京' in address:
            region = '東京23区'
        elif '神奈川' in address:
            region = '神奈川県'
        elif '千葉' in address:
            region = '千葉県'
        elif '埼玉' in address:
            region = '埼玉県'
        else:
            region = 'その他'
        
        region_orders[region].append(order)
    
    for region, region_order_list in region_orders.items():
        processed_count = sum(1 for o in region_order_list if o.id in covered_order_ids)
        print(f"  {region}: {len(region_order_list)}件中{processed_count}件処理済み")

if __name__ == '__main__':
    analyze_july20_plans()
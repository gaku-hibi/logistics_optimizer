#!/usr/bin/env python
"""
既存のUnifiedPalletデータのrelated_ordersフィールドを修正するスクリプト
"""

import os
import sys
import django

# Djangoの設定
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'logistics.settings')
django.setup()

from delivery.models import UnifiedPallet, ShippingOrder

def fix_unified_pallets():
    """UnifiedPalletのrelated_ordersを修正"""
    
    print("UnifiedPalletのrelated_orders修正を開始します...")
    
    # 全てのUnifiedPalletを取得
    unified_pallets = UnifiedPallet.objects.all()
    total_count = unified_pallets.count()
    
    print(f"修正対象のUnifiedPallet数: {total_count}")
    
    fixed_count = 0
    
    for pallet in unified_pallets:
        orders_to_relate = []
        
        if pallet.pallet_type == 'REAL':
            # REALパレットの場合、パレット詳細から注文を取得
            if pallet.pallet_detail:
                # パレットに含まれる全ての商品から注文を取得
                for pallet_item in pallet.pallet_detail.items.all():
                    if pallet_item.shipping_order and pallet_item.shipping_order not in orders_to_relate:
                        orders_to_relate.append(pallet_item.shipping_order)
                
                # related_ordersを設定
                if orders_to_relate:
                    pallet.related_orders.set(orders_to_relate)
                    fixed_count += 1
                    print(f"REALパレット ID={pallet.id}: {len(orders_to_relate)}個の注文を関連付けました")
                else:
                    print(f"警告: REALパレット ID={pallet.id} に関連する注文が見つかりません")
                    
        elif pallet.pallet_type == 'VIRTUAL':
            # VIRTUALパレットの場合、shipping_orderを使用
            if pallet.shipping_order:
                pallet.related_orders.set([pallet.shipping_order])
                fixed_count += 1
                print(f"VIRTUALパレット ID={pallet.id}: 注文ID={pallet.shipping_order.id}を関連付けました")
            else:
                print(f"警告: VIRTUALパレット ID={pallet.id} にshipping_orderがありません")
    
    print(f"\n修正完了: {fixed_count}/{total_count} パレットを修正しました")

if __name__ == '__main__':
    fix_unified_pallets()
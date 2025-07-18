from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.db import transaction
from django.core.paginator import Paginator
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, date
import json

from .models import (
    Item, Part, Shipper, Destination, ShippingOrder, OrderItem,
    Truck, DeliveryPlan, PlanOrderDetail, PlanItemLoad,
    PalletizePlan, PalletDetail, PalletItem, LooseItem, PalletConfiguration,
    UnifiedPallet, LoadPallet, PalletLoadHistory
)
from .forms import ShippingOrderForm, TruckForm, ItemForm, ShipperForm, DestinationForm
from .optimization import DeliveryOptimizer
from .reports import generate_plan_report


def index(request):
    """ダッシュボード"""
    context = {
        'total_orders': ShippingOrder.objects.count(),
        'pending_orders': ShippingOrder.objects.filter(
            planorderdetail__isnull=True
        ).count(),
        'total_plans': DeliveryPlan.objects.count(),
        'total_trucks': Truck.objects.count(),
        'recent_orders': ShippingOrder.objects.order_by('-created_at')[:5],
        'recent_plans': DeliveryPlan.objects.order_by('-created_at')[:5],
    }
    return render(request, 'delivery/index.html', context)


# 出荷依頼管理
def order_list(request):
    """出荷依頼一覧"""
    orders = ShippingOrder.objects.select_related('shipper', 'destination').all()
    
    # 検索フィルター
    search = request.GET.get('search')
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(destination__name__icontains=search) |
            Q(shipper__name__icontains=search)
        )
    
    # 配送日フィルター
    delivery_date = request.GET.get('delivery_date')
    if delivery_date:
        orders = orders.filter(delivery_deadline=delivery_date)
    
    # ページネーション
    paginator = Paginator(orders, 20)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    return render(request, 'delivery/order_list.html', {'orders': orders})


def order_create(request):
    """出荷依頼作成"""
    if request.method == 'POST':
        form = ShippingOrderForm(request.POST)
        if form.is_valid():
            order = form.save()
            messages.success(request, f'出荷依頼 {order.order_number} を作成しました。')
            return redirect('delivery:order_detail', pk=order.pk)
    else:
        form = ShippingOrderForm()
    
    return render(request, 'delivery/order_form.html', {'form': form, 'title': '新規出荷依頼'})


def order_detail(request, pk):
    """出荷依頼詳細"""
    order = get_object_or_404(ShippingOrder, pk=pk)
    order_items = order.order_items.select_related('item').all()
    
    # 重量・体積計算
    total_weight = sum(item.item.weight * item.quantity for item in order_items if item.item.weight)
    total_volume = sum(item.item.volume * item.quantity for item in order_items)
    
    context = {
        'order': order,
        'order_items': order_items,
        'total_weight': total_weight,
        'total_volume': total_volume,
    }
    return render(request, 'delivery/order_detail.html', context)


def order_update(request, pk):
    """出荷依頼更新"""
    order = get_object_or_404(ShippingOrder, pk=pk)
    
    if request.method == 'POST':
        form = ShippingOrderForm(request.POST, instance=order)
        if form.is_valid():
            form.save()
            messages.success(request, f'出荷依頼 {order.order_number} を更新しました。')
            return redirect('delivery:order_detail', pk=order.pk)
    else:
        form = ShippingOrderForm(instance=order)
    
    return render(request, 'delivery/order_form.html', {
        'form': form, 
        'title': f'出荷依頼編集 - {order.order_number}',
        'order': order
    })


# 配送計画管理
def plan_list(request):
    """配送計画一覧"""
    plans = DeliveryPlan.objects.select_related('truck').all()
    
    # 日付フィルター
    plan_date = request.GET.get('plan_date')
    if plan_date:
        plans = plans.filter(plan_date=plan_date)
    
    paginator = Paginator(plans, 20)
    page = request.GET.get('page')
    plans = paginator.get_page(page)
    
    return render(request, 'delivery/plan_list.html', {'plans': plans})


def plan_detail(request, pk):
    """配送計画詳細"""
    plan = get_object_or_404(DeliveryPlan, pk=pk)
    order_details = plan.order_details.select_related('shipping_order__destination').all()
    # 新しいLoadPalletモデルを使用
    load_pallets = plan.load_pallets.select_related('pallet__item', 'pallet__shipping_order').all()
    
    # 後方互換性のため、従来のitem_loadsも取得
    item_loads = plan.item_loads.select_related('item', 'shipping_order').all()
    
    # 関連するパレタイズ計画を取得
    palletize_plan = None
    try:
        # 配送計画の日付に対応するパレタイズ計画を探す
        palletize_plan = PalletizePlan.objects.filter(delivery_date=plan.plan_date).first()
    except Exception as e:
        print(f"パレタイズ計画取得エラー: {e}")
    
    # パレット概要を作成
    pallet_summary = []
    loose_items_summary = []
    
    try:
        # 新しいシステムでパレット情報を取得
        if load_pallets.exists():
            print(f"LoadPallet数: {load_pallets.count()}")
            
            for load_pallet in load_pallets:
                pallet = load_pallet.pallet
                
                if pallet.pallet_type == 'REAL':
                    # REALパレットの場合：パレット詳細から商品情報を取得
                    if pallet.pallet_detail:
                        pallet_items = pallet.pallet_detail.items.select_related('item', 'shipping_order').all()
                        
                        pallet_summary.append({
                            'pallet_number': f"P{pallet.id}",
                            'item_count': pallet_items.count(),
                            'total_weight': pallet.weight,
                            'total_volume': pallet.volume,
                            'items': pallet_items,
                            'position': f"({load_pallet.position_x}, {load_pallet.position_y})",
                            'pallet_type': 'REAL'
                        })
                        
                        print(f"REALパレット #{pallet.id}: 位置({load_pallet.position_x}, {load_pallet.position_y}) - 商品数: {pallet_items.count()}")
                
                elif pallet.pallet_type == 'VIRTUAL':
                    # VIRTUALパレット（バラ積み）の場合
                    loose_items_summary.append({
                        'item': pallet.item,
                        'width': pallet.width,
                        'depth': pallet.depth,
                        'height': pallet.height,
                        'weight': pallet.weight,
                        'volume': pallet.volume,
                        'quantity': pallet.item_quantity,
                        'position': f"({load_pallet.position_x}, {load_pallet.position_y})"
                    })
                    
                    print(f"VIRTUALパレット #{pallet.id}: バラ積み商品 {pallet.item.name}")
        
        # 後方互換性：従来のitem_loadsがある場合（旧システムでの計画）
        elif item_loads.exists():
            print(f"従来のitem_loads数: {item_loads.count()}")
            
            # 従来のロジックを使用
            pallet_config = PalletConfiguration.get_default()
            pallet_width = pallet_config.width
            pallet_depth = pallet_config.depth
            
            # 位置ベースでパレットを検出
            pallet_grid = {}
            processed_item_loads = set()
            
            for load in item_loads:
                if load.id in processed_item_loads:
                    continue
                    
                # 商品の位置をパレットグリッドに変換
                grid_x = (load.position_x // pallet_width) * pallet_width
                grid_y = (load.position_y // pallet_depth) * pallet_depth
                grid_key = f"{grid_x},{grid_y}"
                
                if grid_key not in pallet_grid:
                    pallet_grid[grid_key] = {
                        'x': grid_x,
                        'y': grid_y,
                        'items': [],
                        'pallet_number': len(pallet_grid) + 1
                    }
                
                pallet_grid[grid_key]['items'].append(load)
                processed_item_loads.add(load.id)
            
            # 検出されたパレットの概要を作成
            for grid_key, grid_info in pallet_grid.items():
                items = grid_info['items']
                if len(items) > 1:  # 複数の商品がある場合のみパレットとして扱う
                    total_weight = sum(item.item.weight * item.quantity for item in items if item.item.weight)
                    total_volume = sum(
                        (item.item.width or 50) * (item.item.depth or 50) * (item.item.height or 50) * item.quantity 
                        for item in items
                    )
                    
                    pallet_summary.append({
                        'pallet_number': grid_info['pallet_number'],
                        'item_count': len(items),
                        'total_weight': total_weight,
                        'total_volume': total_volume,
                        'items': items,
                        'position': f"({grid_info['x']}, {grid_info['y']})",
                        'pallet_type': 'LEGACY'
                    })
                else:
                    # 単一商品はバラ積みとして扱う
                    item = items[0]
                    volume = (item.item.width or 50) * (item.item.depth or 50) * (item.item.height or 50) * item.quantity
                    weight = (item.item.weight or 0) * item.quantity
                    
                    loose_items_summary.append({
                        'item': item.item,
                        'width': item.item.width or 50,
                        'depth': item.item.depth or 50,
                        'height': item.item.height or 50,
                        'weight': item.item.weight or 0,
                        'volume': volume,
                        'quantity': item.quantity,
                        'position': f"({grid_info['x']}, {grid_info['y']})"
                    })
            
        print(f"最終パレット概要数: {len(pallet_summary)}")
        print(f"最終バラ積み商品数: {len(loose_items_summary)}")
            
    except Exception as e:
        print(f"パレット概要作成エラー: {e}")
        messages.warning(request, f'パレット概要の作成でエラーが発生しました: {e}')
    
    # トラック積載の可視化データ（パレットとバラ積みを区別）
    truck_layout = {
        'width': plan.truck.width,
        'depth': plan.truck.depth,
        'pallets': [],
        'loose_items': []
    }
    
    # パレット配置の正確な表示のため、より単純なアプローチを採用
    # 新システムではload_palletsから直接取得、旧システムではitem_loadsから推定
    if load_pallets.exists():
        # 新システム: LoadPalletから直接可視化データを作成
        for load_pallet in load_pallets:
            pallet = load_pallet.pallet
            
            if pallet.pallet_type == 'REAL':
                # REALパレットの場合
                # パレット内の商品情報を取得
                pallet_items = []
                if pallet.pallet_detail:
                    detail_items = pallet.pallet_detail.items.select_related('item').all()
                    for detail_item in detail_items:
                        pallet_items.append({
                            'name': detail_item.item.name,
                            'x': detail_item.position_x,
                            'y': detail_item.position_y,
                            'width': detail_item.width,
                            'depth': detail_item.depth,
                            'quantity': 1  # PalletItemには個別の数量がないため1とする
                        })
                
                truck_layout['pallets'].append({
                    'x': load_pallet.position_x,
                    'y': load_pallet.position_y,
                    'width': pallet.width,
                    'depth': pallet.depth,
                    'name': f'パレット#{pallet.id}',
                    'pallet_number': pallet.id,
                    'rotation': load_pallet.rotation,
                    'type': 'REAL',
                    'items': pallet_items
                })
            elif pallet.pallet_type == 'VIRTUAL':
                # VIRTUALパレット（バラ積み）の場合
                truck_layout['loose_items'].append({
                    'x': load_pallet.position_x,
                    'y': load_pallet.position_y,
                    'width': pallet.width,
                    'depth': pallet.depth,
                    'name': pallet.item.name,
                    'quantity': pallet.item_quantity,
                    'rotation': load_pallet.rotation,
                    'type': 'VIRTUAL'
                })
    
    elif item_loads.exists():
        # 旧システム: item_loadsから推定
        # パレット設定を取得
        pallet_config = PalletConfiguration.get_default()
        pallet_width = pallet_config.width
        pallet_depth = pallet_config.depth
        
        print(f"積載商品数: {item_loads.count()}")
        
        # 商品の位置から自動的にパレットを検出
        # 110cm x 110cm のグリッドに基づいてパレットを配置
        pallet_grid = {}
        processed_item_loads = set()
        
        for load in item_loads:
            if load.id in processed_item_loads:
                continue
                
            # 商品の位置をパレットグリッドに変換
            grid_x = (load.position_x // pallet_width) * pallet_width
            grid_y = (load.position_y // pallet_depth) * pallet_depth
            grid_key = f"{grid_x},{grid_y}"
            
            if grid_key not in pallet_grid:
                pallet_grid[grid_key] = {
                    'x': grid_x,
                    'y': grid_y,
                    'width': pallet_width,
                    'depth': pallet_depth,
                    'items': [],
                    'pallet_number': len(pallet_grid) + 1
                }
            
            # 商品をパレットに追加
            pallet_grid[grid_key]['items'].append({
                'name': load.item.name,
                'quantity': load.quantity,
                'x': load.position_x - grid_x,  # パレット内の相対位置
                'y': load.position_y - grid_y,
                'width': load.item.width or 50,
                'depth': load.item.depth or 50
            })
            
            processed_item_loads.add(load.id)
            print(f"商品 {load.item.name} を グリッド ({grid_x}, {grid_y}) に配置")
        
        # パレット配置をトラックレイアウトに追加
        truck_layout['pallets'] = list(pallet_grid.values())
        print(f"\n最終的なパレット配置数: {len(truck_layout['pallets'])}")
        
        # パレットの詳細を表示
        for pallet in truck_layout['pallets']:
            print(f"パレット #{pallet['pallet_number']}: 位置({pallet['x']}, {pallet['y']}) - 商品数: {len(pallet['items'])}")
        
        # 残りの商品（バラ積み）を処理
        for load in item_loads:
            if load.id not in processed_item_loads:
                truck_layout['loose_items'].append({
                    'x': load.position_x,
                    'y': load.position_y,
                    'width': load.item.width or 50,
                    'depth': load.item.depth or 50,
                    'name': load.item.name,
                    'quantity': load.quantity,
                    'rotation': load.rotation
                })
    else:
        # パレタイズ設計結果がない場合は全てバラ積みとして扱う
        for load in item_loads:
            truck_layout['loose_items'].append({
                'x': load.position_x,
                'y': load.position_y,
                'width': load.item.width or 50,
                'depth': load.item.depth or 50,
                'name': load.item.name,
                'quantity': load.quantity,
                'rotation': load.rotation
            })
    
    # バラ積み商品の統計を計算
    total_loose_weight = sum(item.get('weight', 0) * item.get('quantity', 1) for item in loose_items_summary)
    total_loose_volume = sum(item.get('volume', 0) for item in loose_items_summary)
    
    context = {
        'plan': plan,
        'order_details': order_details,
        'item_loads': item_loads,  # 後方互換性のため
        'load_pallets': load_pallets,  # 新しいシステム
        'truck_layout': json.dumps(truck_layout),
        'pallet_summary': pallet_summary,
        'loose_items_summary': loose_items_summary,
        'pallet_count': len(pallet_summary),
        'loose_items_count': len(loose_items_summary),
        'palletize_plan': palletize_plan,
        'total_loose_weight': total_loose_weight,
        'total_loose_volume': total_loose_volume,
    }
    return render(request, 'delivery/plan_detail.html', context)


def plan_delete(request, pk):
    """配送計画削除"""
    plan = get_object_or_404(DeliveryPlan, pk=pk)
    
    if request.method == 'POST':
        try:
            plan_id = plan.id
            plan_date = plan.plan_date
            plan.delete()
            messages.success(request, f'配送計画 {plan_id} ({plan_date}) を削除しました。')
            return redirect('delivery:plan_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:plan_detail', pk=pk)
    
    # 関連データの数を取得
    order_details_count = plan.order_details.count()
    item_loads_count = plan.item_loads.count()
    
    return render(request, 'delivery/plan_confirm_delete.html', {
        'plan': plan,
        'order_details_count': order_details_count,
        'item_loads_count': item_loads_count
    })


def plan_delete_all(request):
    """配送計画全削除"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                deleted_count = DeliveryPlan.objects.count()
                DeliveryPlan.objects.all().delete()
            messages.success(request, f'{deleted_count}件の配送計画を全削除しました。')
        except Exception as e:
            messages.error(request, f'全削除に失敗しました: {str(e)}')
        return redirect('delivery:plan_list')
    
    return redirect('delivery:plan_list')


def optimize_delivery(request):
    """配送最適化実行"""
    if request.method == 'POST':
        target_date = request.POST.get('target_date')
        if not target_date:
            messages.error(request, '対象日を選択してください。')
            return redirect('delivery:optimize_delivery')
        
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            # パレタイズ設計が完了しているかチェック
            if not PalletizePlan.objects.filter(delivery_date=target_date).exists():
                messages.error(request, f'{target_date} のパレタイズ設計が完了していません。先にパレタイズ設計を実行してください。')
                return redirect('delivery:optimize_delivery')
            
            # 対象日の未配送依頼を取得
            pending_orders = ShippingOrder.objects.filter(
                delivery_deadline=target_date,
                planorderdetail__isnull=True
            ).select_related('shipper', 'destination').prefetch_related('order_items__item')
            
            if not pending_orders.exists():
                messages.warning(request, f'{target_date} の未配送依頼はありません。')
                return redirect('delivery:optimize_delivery')
            
            # トラックが登録されているかチェック
            if not Truck.objects.exists():
                messages.error(request, 'トラックが登録されていません。トラックマスタにトラックを登録してください。')
                return redirect('delivery:optimize_delivery')
            
            # 商品に寸法・重量が設定されているかチェック
            items_without_dimensions = []
            for order in pending_orders:
                for order_item in order.order_items.all():
                    item = order_item.item
                    if item.parts.exists():
                        # セット品の場合、部品をチェック
                        for part in item.parts.all():
                            if not all([part.width, part.depth, part.height, part.weight]):
                                items_without_dimensions.append(f"{item.name}の部品{part.parts_code}")
                    else:
                        # 単品の場合
                        if not all([item.width, item.depth, item.height, item.weight]):
                            items_without_dimensions.append(item.name)
            
            if items_without_dimensions:
                messages.error(request, f'以下の商品に寸法または重量が設定されていません: {", ".join(items_without_dimensions[:5])}{"..." if len(items_without_dimensions) > 5 else ""}')
                return redirect('delivery:optimize_delivery')
            
            # デバッグ情報を出力
            print(f"=== 最適化開始 ===")
            print(f"対象日: {target_date}")
            print(f"未配送依頼数: {pending_orders.count()}")
            print(f"利用可能トラック数: {Truck.objects.count()}")
            
            # パレタイズ設計の確認
            palletize_plan = PalletizePlan.objects.filter(delivery_date=target_date).first()
            if palletize_plan:
                print(f"パレタイズ設計ID: {palletize_plan.id}")
                print(f"パレット数: {palletize_plan.pallets.count()}")
                print(f"バラ積み商品数: {palletize_plan.loose_items.count()}")
            
            # 最適化実行（統一パレットシステムを使用）
            optimizer = DeliveryOptimizer()
            plans = optimizer.optimize_with_unified_pallets(pending_orders, target_date)
            
            print(f"作成された配送計画数: {len(plans) if plans else 0}")
            
            if plans:
                messages.success(request, f'{len(plans)} 件の配送計画を作成しました。')
                return redirect('delivery:plan_list')
            else:
                messages.error(request, '最適化に失敗しました。詳細はサーバーログをご確認ください。')
                
        except Exception as e:
            print(f"最適化エラー: {str(e)}")
            import traceback
            traceback.print_exc()
            messages.error(request, f'エラーが発生しました: {str(e)}')
    
    # パレタイズ設計が完了した日付のみを取得
    palletized_dates = PalletizePlan.objects.values_list('delivery_date', flat=True).distinct().order_by('delivery_date')
    
    # 各日付について未配送依頼があるかチェック
    available_dates = []
    for date in palletized_dates:
        pending_count = ShippingOrder.objects.filter(
            delivery_deadline=date,
            planorderdetail__isnull=True
        ).count()
        if pending_count > 0:
            available_dates.append({
                'date': date,
                'pending_count': pending_count
            })
    
    return render(request, 'delivery/optimize.html', {
        'available_dates': available_dates
    })




# トラック管理
def truck_list(request):
    """トラック一覧"""
    trucks = Truck.objects.all()
    return render(request, 'delivery/truck_list.html', {'trucks': trucks})


def truck_create(request):
    """トラック作成"""
    if request.method == 'POST':
        form = TruckForm(request.POST)
        if form.is_valid():
            truck = form.save()
            messages.success(request, 'トラックを登録しました。')
            return redirect('delivery:truck_detail', pk=truck.pk)
    else:
        form = TruckForm()
    
    return render(request, 'delivery/truck_form.html', {'form': form, 'title': '新規トラック登録'})


def truck_detail(request, pk):
    """トラック詳細"""
    truck = get_object_or_404(Truck, pk=pk)
    recent_plans = DeliveryPlan.objects.filter(truck=truck).order_by('-created_at')[:10]
    
    return render(request, 'delivery/truck_detail.html', {
        'truck': truck,
        'recent_plans': recent_plans
    })


def truck_update(request, pk):
    """トラック編集"""
    truck = get_object_or_404(Truck, pk=pk)
    
    if request.method == 'POST':
        form = TruckForm(request.POST, instance=truck)
        if form.is_valid():
            truck = form.save()
            messages.success(request, f'トラック {truck.shipping_company} {truck.truck_class} を更新しました。')
            return redirect('delivery:truck_detail', pk=truck.pk)
    else:
        form = TruckForm(instance=truck)
    
    return render(request, 'delivery/truck_form.html', {
        'form': form, 
        'title': f'トラック編集 - {truck.shipping_company} {truck.truck_class}',
        'truck': truck
    })


def truck_delete(request, pk):
    """トラック削除"""
    truck = get_object_or_404(Truck, pk=pk)
    
    if request.method == 'POST':
        try:
            truck_info = f'{truck.shipping_company} {truck.truck_class}'
            truck.delete()
            messages.success(request, f'トラック {truck_info} を削除しました。')
            return redirect('delivery:truck_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:truck_detail', pk=pk)
    
    # 関連する配送計画の数を取得
    related_plans_count = DeliveryPlan.objects.filter(truck=truck).count()
    
    return render(request, 'delivery/truck_confirm_delete.html', {
        'truck': truck,
        'related_plans_count': related_plans_count
    })


# 商品管理
def item_list(request):
    """商品一覧"""
    items = Item.objects.all()
    
    search = request.GET.get('search')
    if search:
        items = items.filter(
            Q(item_code__icontains=search) |
            Q(name__icontains=search)
        )
    
    paginator = Paginator(items, 20)
    page = request.GET.get('page')
    items = paginator.get_page(page)
    
    return render(request, 'delivery/item_list.html', {'items': items})


def item_create(request):
    """商品作成"""
    if request.method == 'POST':
        form = ItemForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'商品 {item.name} を登録しました。')
            return redirect('delivery:item_detail', pk=item.pk)
    else:
        form = ItemForm()
    
    return render(request, 'delivery/item_form.html', {'form': form, 'title': '新規商品登録'})


def item_detail(request, pk):
    """商品詳細"""
    item = get_object_or_404(Item, pk=pk)
    parts = item.parts.all()
    
    return render(request, 'delivery/item_detail.html', {
        'item': item,
        'parts': parts
    })


def item_update(request, pk):
    """商品編集"""
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        form = ItemForm(request.POST, instance=item)
        if form.is_valid():
            item = form.save()
            messages.success(request, f'商品 {item.name} を更新しました。')
            return redirect('delivery:item_detail', pk=item.pk)
    else:
        form = ItemForm(instance=item)
    
    return render(request, 'delivery/item_form.html', {
        'form': form, 
        'title': f'商品編集 - {item.name}',
        'item': item
    })


def item_delete(request, pk):
    """商品削除"""
    item = get_object_or_404(Item, pk=pk)
    
    if request.method == 'POST':
        try:
            item_name = item.name
            item.delete()
            messages.success(request, f'商品 {item_name} を削除しました。')
            return redirect('delivery:item_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:item_detail', pk=pk)
    
    # 関連する出荷依頼商品の数を取得
    related_order_items_count = OrderItem.objects.filter(item=item).count()
    
    return render(request, 'delivery/item_confirm_delete.html', {
        'item': item,
        'related_order_items_count': related_order_items_count
    })


# マスタ一覧
def shipper_list(request):
    """荷主一覧"""
    shippers = Shipper.objects.all()
    return render(request, 'delivery/shipper_list.html', {'shippers': shippers})


def destination_list(request):
    """配送先一覧"""
    destinations = Destination.objects.all()
    return render(request, 'delivery/destination_list.html', {'destinations': destinations})


def shipper_create(request):
    """荷主作成"""
    if request.method == 'POST':
        form = ShipperForm(request.POST)
        if form.is_valid():
            shipper = form.save()
            messages.success(request, f'荷主 {shipper.name} を登録しました。')
            return redirect('delivery:shipper_list')
    else:
        form = ShipperForm()
    
    return render(request, 'delivery/shipper_form.html', {'form': form, 'title': '新規荷主登録'})


def destination_create(request):
    """配送先作成"""
    if request.method == 'POST':
        form = DestinationForm(request.POST)
        if form.is_valid():
            destination = form.save()
            messages.success(request, f'配送先 {destination.name} を登録しました。')
            return redirect('delivery:destination_list')
    else:
        form = DestinationForm()
    
    return render(request, 'delivery/destination_form.html', {'form': form, 'title': '新規配送先登録'})


def shipper_detail(request, pk):
    """荷主詳細"""
    shipper = get_object_or_404(Shipper, pk=pk)
    recent_orders = ShippingOrder.objects.filter(shipper=shipper).order_by('-created_at')[:10]
    
    return render(request, 'delivery/shipper_detail.html', {
        'shipper': shipper,
        'recent_orders': recent_orders
    })


def shipper_update(request, pk):
    """荷主編集"""
    shipper = get_object_or_404(Shipper, pk=pk)
    
    if request.method == 'POST':
        form = ShipperForm(request.POST, instance=shipper)
        if form.is_valid():
            shipper = form.save()
            messages.success(request, f'荷主 {shipper.name} を更新しました。')
            return redirect('delivery:shipper_detail', pk=shipper.pk)
    else:
        form = ShipperForm(instance=shipper)
    
    return render(request, 'delivery/shipper_form.html', {
        'form': form, 
        'title': f'荷主編集 - {shipper.name}',
        'shipper': shipper
    })


def shipper_delete(request, pk):
    """荷主削除"""
    shipper = get_object_or_404(Shipper, pk=pk)
    
    if request.method == 'POST':
        try:
            shipper_name = shipper.name
            shipper.delete()
            messages.success(request, f'荷主 {shipper_name} を削除しました。')
            return redirect('delivery:shipper_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:shipper_detail', pk=pk)
    
    # 関連する出荷依頼の数を取得
    related_orders_count = ShippingOrder.objects.filter(shipper=shipper).count()
    
    return render(request, 'delivery/shipper_confirm_delete.html', {
        'shipper': shipper,
        'related_orders_count': related_orders_count
    })


def destination_detail(request, pk):
    """配送先詳細"""
    destination = get_object_or_404(Destination, pk=pk)
    recent_orders = ShippingOrder.objects.filter(destination=destination).order_by('-created_at')[:10]
    
    return render(request, 'delivery/destination_detail.html', {
        'destination': destination,
        'recent_orders': recent_orders
    })


def destination_update(request, pk):
    """配送先編集"""
    destination = get_object_or_404(Destination, pk=pk)
    
    if request.method == 'POST':
        form = DestinationForm(request.POST, instance=destination)
        if form.is_valid():
            destination = form.save()
            messages.success(request, f'配送先 {destination.name} を更新しました。')
            return redirect('delivery:destination_detail', pk=destination.pk)
    else:
        form = DestinationForm(instance=destination)
    
    return render(request, 'delivery/destination_form.html', {
        'form': form, 
        'title': f'配送先編集 - {destination.name}',
        'destination': destination
    })


def destination_delete(request, pk):
    """配送先削除"""
    destination = get_object_or_404(Destination, pk=pk)
    
    if request.method == 'POST':
        try:
            destination_name = destination.name
            destination.delete()
            messages.success(request, f'配送先 {destination_name} を削除しました。')
            return redirect('delivery:destination_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:destination_detail', pk=pk)
    
    # 関連する出荷依頼の数を取得
    related_orders_count = ShippingOrder.objects.filter(destination=destination).count()
    
    return render(request, 'delivery/destination_confirm_delete.html', {
        'destination': destination,
        'related_orders_count': related_orders_count
    })


# レポート
def plan_report(request, plan_id):
    """配送計画レポート（PDF出力）"""
    plan = get_object_or_404(DeliveryPlan, pk=plan_id)
    
    try:
        pdf_buffer = generate_plan_report(plan)
        response = HttpResponse(pdf_buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="delivery_plan_{plan.id}.pdf"'
        return response
    except Exception as e:
        messages.error(request, f'PDF生成エラー: {str(e)}')
        return redirect('delivery:plan_detail', pk=plan_id)


# データインポート
def data_import(request):
    """データインポート"""
    if request.method == 'POST':
        # CSVインポートのロジック（簡易版）
        messages.info(request, 'データインポート機能は実装中です。')
    
    return render(request, 'delivery/data_import.html')


# パレタイズ設計
def palletize_design(request):
    """パレタイズ設計画面"""
    if request.method == 'POST':
        delivery_date = request.POST.get('delivery_date')
        if delivery_date:
            return redirect('delivery:palletize_result', delivery_date=delivery_date)
    
    # 配送日の選択肢を取得（出荷依頼のある日付）
    delivery_dates = ShippingOrder.objects.values_list(
        'delivery_deadline', flat=True
    ).distinct().order_by('delivery_deadline')
    
    return render(request, 'delivery/palletize_design.html', {
        'delivery_dates': delivery_dates
    })


def palletize_result(request, delivery_date):
    """パレタイズ設計結果"""
    from .optimization import PalletOptimizer, Box
    
    # 指定日の出荷依頼を取得
    orders = ShippingOrder.objects.filter(
        delivery_deadline=delivery_date
    ).select_related('shipper', 'destination')
    
    if not orders.exists():
        messages.error(request, f'{delivery_date}の出荷依頼が見つかりません。')
        return redirect('delivery:palletize_design')
    
    # 商品情報を収集
    all_items = []
    for order in orders:
        order_items = order.order_items.select_related('item').all()
        for order_item in order_items:
            item = order_item.item
            # セット品の場合は部品を展開
            if item.parts.exists():
                for part in item.parts.all():
                    for _ in range(order_item.quantity):
                        all_items.append({
                            'order': order,
                            'item': item,
                            'part': part,
                            'box': Box(
                                width=part.width,
                                depth=part.depth,
                                height=part.height,
                                weight=part.weight,
                                item_code=part.parts_code,
                                shipping_order_id=order.id
                            )
                        })
            else:
                # 単品の場合
                for _ in range(order_item.quantity):
                    all_items.append({
                        'order': order,
                        'item': item,
                        'part': None,
                        'box': Box(
                            width=item.width,
                            depth=item.depth,
                            height=item.height,
                            weight=item.weight,
                            item_code=item.item_code,
                            shipping_order_id=order.id
                        )
                    })
    
    # パレタイズ最適化
    optimizer = PalletOptimizer()
    boxes = [item['box'] for item in all_items]
    pallets, remaining_boxes = optimizer.pack_pallet(boxes)
    
    # 結果をデータベースに保存
    with transaction.atomic():
        # パレタイズ設計を作成
        palletize_plan = PalletizePlan.objects.create(
            delivery_date=delivery_date,
            total_items=len(boxes),
            total_pallets=len(pallets),
            total_loose_items=len(remaining_boxes)
        )
        
        # パレット詳細を保存
        for i, pallet in enumerate(pallets):
            pallet_detail = PalletDetail.objects.create(
                palletize_plan=palletize_plan,
                pallet_number=i + 1,
                total_weight=pallet.get_total_weight(),
                total_volume=pallet.get_used_volume(),
                utilization=(pallet.get_used_volume() / (pallet.width * pallet.depth * pallet.height)) * 100
            )
            
            # パレット積載商品を保存
            for box in pallet.boxes:
                item_info = next(item for item in all_items if item['box'] == box)
                PalletItem.objects.create(
                    pallet=pallet_detail,
                    shipping_order=item_info['order'],
                    item=item_info['item'],
                    part=item_info['part'],
                    position_x=box.x,
                    position_y=box.y,
                    position_z=box.z,
                    width=box.width,
                    depth=box.depth,
                    height=box.height,
                    weight=box.weight
                )
        
        # バラ積み商品を保存
        for box in remaining_boxes:
            item_info = next(item for item in all_items if item['box'] == box)
            reason = 'パレットサイズ超過' if (box.width > 110 or box.depth > 110) else '積載不可'
            LooseItem.objects.create(
                palletize_plan=palletize_plan,
                shipping_order=item_info['order'],
                item=item_info['item'],
                width=box.width,
                depth=box.depth,
                height=box.height,
                weight=box.weight,
                reason=reason
            )
    
    messages.success(request, f'パレタイズ設計を保存しました。（ID: {palletize_plan.id}）')
    
    # 結果を整理（表示用）
    pallet_results = []
    for i, pallet in enumerate(pallets):
        pallet_info = {
            'number': i + 1,
            'items': [],
            'total_weight': pallet.get_total_weight(),
            'total_volume': pallet.get_used_volume(),
            'utilization': (pallet.get_used_volume() / (pallet.width * pallet.depth * pallet.height)) * 100
        }
        
        for box in pallet.boxes:
            # 該当する商品情報を検索
            item_info = next(item for item in all_items if item['box'] == box)
            
            pallet_info['items'].append({
                'item': item_info['item'],
                'part': item_info['part'],
                'order': item_info['order'],
                'position': (box.x, box.y, box.z),
                'rotation': 0  # 今回は回転なし
            })
        
        pallet_results.append(pallet_info)
    
    # パレットに載らない商品（バラ積み）
    loose_items = []
    for box in remaining_boxes:
        item_info = next(item for item in all_items if item['box'] == box)
        loose_items.append(item_info)
    
    # パレット設定を取得
    pallet_config = PalletConfiguration.get_default()
    
    context = {
        'delivery_date': delivery_date,
        'orders': orders,
        'pallets': pallet_results,
        'loose_items': loose_items,
        'total_pallets': len(pallets),
        'total_items': len(boxes),
        'palletize_plan': palletize_plan,
        'pallet_config': pallet_config
    }
    
    return render(request, 'delivery/palletize_result.html', context)


def palletize_list(request):
    """パレタイズ設計一覧"""
    palletize_plans = PalletizePlan.objects.all()
    
    # 検索フィルター
    delivery_date = request.GET.get('delivery_date')
    if delivery_date:
        palletize_plans = palletize_plans.filter(delivery_date=delivery_date)
    
    # ページネーション
    paginator = Paginator(palletize_plans, 20)
    page = request.GET.get('page')
    palletize_plans = paginator.get_page(page)
    
    return render(request, 'delivery/palletize_list.html', {
        'palletize_plans': palletize_plans
    })


def palletize_detail(request, pk):
    """パレタイズ設計詳細"""
    palletize_plan = get_object_or_404(PalletizePlan, pk=pk)
    
    # 関連する出荷依頼を取得
    order_ids = set()
    for pallet in palletize_plan.pallets.all():
        for item in pallet.items.all():
            order_ids.add(item.shipping_order.id)
    for loose_item in palletize_plan.loose_items.all():
        order_ids.add(loose_item.shipping_order.id)
    
    orders = ShippingOrder.objects.filter(id__in=order_ids)
    
    # パレット設定を取得
    pallet_config = PalletConfiguration.get_default()
    
    return render(request, 'delivery/palletize_detail.html', {
        'palletize_plan': palletize_plan,
        'orders': orders,
        'pallet_config': pallet_config
    })


def palletize_delete(request, pk):
    """パレタイズ設計削除"""
    palletize_plan = get_object_or_404(PalletizePlan, pk=pk)
    
    if request.method == 'POST':
        try:
            plan_id = palletize_plan.id
            delivery_date = palletize_plan.delivery_date
            palletize_plan.delete()
            messages.success(request, f'パレタイズ設計 {plan_id} ({delivery_date}) を削除しました。')
            return redirect('delivery:palletize_list')
        except Exception as e:
            messages.error(request, f'削除に失敗しました: {str(e)}')
            return redirect('delivery:palletize_detail', pk=pk)
    
    # 関連データの数を取得
    pallets_count = palletize_plan.pallets.count()
    pallet_items_count = sum(pallet.items.count() for pallet in palletize_plan.pallets.all())
    loose_items_count = palletize_plan.loose_items.count()
    
    # 関連する出荷依頼を取得
    order_ids = set()
    for pallet in palletize_plan.pallets.all():
        for item in pallet.items.all():
            order_ids.add(item.shipping_order.id)
    for loose_item in palletize_plan.loose_items.all():
        order_ids.add(loose_item.shipping_order.id)
    
    related_orders_count = len(order_ids)
    
    return render(request, 'delivery/palletize_confirm_delete.html', {
        'palletize_plan': palletize_plan,
        'pallets_count': pallets_count,
        'pallet_items_count': pallet_items_count,
        'loose_items_count': loose_items_count,
        'related_orders_count': related_orders_count
    })


def palletize_delete_all(request):
    """パレタイズ設計全削除"""
    if request.method == 'POST':
        try:
            with transaction.atomic():
                deleted_count = PalletizePlan.objects.count()
                PalletizePlan.objects.all().delete()
            messages.success(request, f'{deleted_count}件のパレタイズ設計を全削除しました。')
        except Exception as e:
            messages.error(request, f'全削除に失敗しました: {str(e)}')
        return redirect('delivery:palletize_list')
    
    return redirect('delivery:palletize_list')
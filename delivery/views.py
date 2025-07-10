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
    Item, Shipper, Destination, ShippingOrder, OrderItem,
    Truck, DeliveryPlan, PlanOrderDetail, PlanItemLoad
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
    item_loads = plan.item_loads.select_related('item', 'shipping_order').all()
    
    # トラック積載の可視化データ
    truck_layout = {
        'width': plan.truck.width,
        'depth': plan.truck.depth,
        'items': []
    }
    
    for load in item_loads:
        truck_layout['items'].append({
            'x': load.position_x,
            'y': load.position_y,
            'width': load.item.width or 50,
            'depth': load.item.depth or 50,
            'name': load.item.name,
            'quantity': load.quantity,
            'rotation': load.rotation
        })
    
    context = {
        'plan': plan,
        'order_details': order_details,
        'item_loads': item_loads,
        'truck_layout': json.dumps(truck_layout),
    }
    return render(request, 'delivery/plan_detail.html', context)


def optimize_delivery(request):
    """配送最適化実行"""
    if request.method == 'POST':
        target_date = request.POST.get('target_date')
        if not target_date:
            messages.error(request, '対象日を選択してください。')
            return redirect('delivery:optimize_delivery')
        
        try:
            target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            
            # 対象日の未配送依頼を取得
            pending_orders = ShippingOrder.objects.filter(
                delivery_deadline=target_date,
                planorderdetail__isnull=True
            )
            
            if not pending_orders.exists():
                messages.warning(request, f'{target_date} の未配送依頼はありません。')
                return redirect('delivery:optimize_delivery')
            
            # 最適化実行
            optimizer = DeliveryOptimizer()
            plans = optimizer.optimize(pending_orders, target_date)
            
            if plans:
                messages.success(request, f'{len(plans)} 件の配送計画を作成しました。')
                return redirect('delivery:plan_list')
            else:
                messages.error(request, '最適化に失敗しました。')
                
        except Exception as e:
            messages.error(request, f'エラーが発生しました: {str(e)}')
    
    # 未配送依頼のある日付を取得
    pending_dates = ShippingOrder.objects.filter(
        planorderdetail__isnull=True
    ).values_list('delivery_deadline', flat=True).distinct().order_by('delivery_deadline')
    
    return render(request, 'delivery/optimize.html', {
        'pending_dates': pending_dates
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
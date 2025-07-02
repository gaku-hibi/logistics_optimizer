from django.shortcuts import render, redirect
from django.views.generic import ListView, TemplateView
from django.contrib import messages
from django.utils import timezone
from datetime import datetime
import json

from .models import Product, Truck, Shipper, DeliveryPlan, TruckAssignment, ProductAssignment
from .algorithms import DeliveryOptimizer


class IndexView(TemplateView):
    template_name = 'delivery/index.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['product_count'] = Product.objects.count()
        context['truck_count'] = Truck.objects.count()
        context['shipper_count'] = Shipper.objects.count()
        return context


class ProductListView(ListView):
    model = Product
    template_name = 'delivery/product_list.html'
    context_object_name = 'products'
    paginate_by = 20
    
    def get_queryset(self):
        return Product.objects.select_related('shipper').order_by('-created_at')


class TruckListView(ListView):
    model = Truck
    template_name = 'delivery/truck_list.html'
    context_object_name = 'trucks'
    paginate_by = 20
    
    def get_queryset(self):
        return Truck.objects.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # 荷台面積を平方メートルに変換
        for truck in context['trucks']:
            truck.bed_area_m2 = truck.bed_area / 10000  # cm² to m²
        return context


class OptimizeView(TemplateView):
    template_name = 'delivery/optimize.html'
    
    def post(self, request, *args, **kwargs):
        # フォームデータを取得
        dispatch_date = request.POST.get('dispatch_date')
        dispatch_time = request.POST.get('dispatch_time')
        depot_address = request.POST.get('depot_address', '東京都千代田区丸の内1-9-1')
        
        # 発送日時を作成
        dispatch_datetime = datetime.strptime(
            f"{dispatch_date} {dispatch_time}", 
            "%Y-%m-%d %H:%M"
        )
        dispatch_datetime = timezone.make_aware(dispatch_datetime)
        
        # 配送期限が発送日以降の商品を取得
        products = Product.objects.filter(
            delivery_deadline__date__gte=dispatch_date
        ).select_related('shipper')
        
        if not products.exists():
            messages.warning(request, '配送対象の商品がありません。')
            return redirect('delivery:optimize')
        
        # トラック情報を取得
        trucks = Truck.objects.all()
        
        if not trucks.exists():
            messages.error(request, 'トラックが登録されていません。')
            return redirect('delivery:optimize')
        
        # 最適化実行
        optimizer = DeliveryOptimizer()
        
        # データを辞書形式に変換
        products_data = []
        for product in products:
            products_data.append({
                'id': product.id,
                'name': product.name,
                'shipper_name': product.shipper.name,
                'width': product.width,
                'depth': product.depth,
                'height': product.height,
                'weight': product.weight,
                'destination_address': product.destination_address,
                'delivery_deadline': product.delivery_deadline
            })
        
        trucks_data = []
        for truck in trucks:
            trucks_data.append({
                'id': truck.id,
                'name': truck.name,
                'bed_width': truck.bed_width,
                'bed_depth': truck.bed_depth,
                'max_weight': truck.max_weight
            })
        
        # 最適化実行
        try:
            results = optimizer.optimize_delivery(
                products_data, 
                trucks_data, 
                dispatch_datetime,
                depot_address
            )
            
            # 結果にトラック情報を追加
            for assignment in results['truck_assignments']:
                truck = next(t for t in trucks_data if t['id'] == assignment['truck_id'])
                assignment['truck_width'] = truck['bed_width']
                assignment['truck_depth'] = truck['bed_depth']
                
                # パッキングデータをJSON形式で準備
                packing_data = []
                for item in assignment['packer'].packed_items:
                    packing_data.append({
                        'id': item['id'],
                        'x': item['x'],
                        'y': item['y'],
                        'width': item['width'],
                        'depth': item['depth']
                    })
                assignment['packing_data'] = json.dumps(packing_data)
            
            messages.success(request, '最適化が完了しました。')
            
        except Exception as e:
            messages.error(request, f'最適化中にエラーが発生しました: {str(e)}')
            results = None
        
        context = self.get_context_data()
        context['results'] = results
        return render(request, self.template_name, context)
from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    # Home
    path('', views.index, name='index'),
    
    # 出荷依頼
    path('orders/', views.order_list, name='order_list'),
    path('orders/new/', views.order_create, name='order_create'),
    path('orders/<int:pk>/', views.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', views.order_update, name='order_update'),
    
    # 配送計画
    path('plans/', views.plan_list, name='plan_list'),
    path('plans/<int:pk>/', views.plan_detail, name='plan_detail'),
    path('plans/optimize/', views.optimize_delivery, name='optimize_delivery'),
    
    # トラック
    path('trucks/', views.truck_list, name='truck_list'),
    path('trucks/new/', views.truck_create, name='truck_create'),
    path('trucks/<int:pk>/', views.truck_detail, name='truck_detail'),
    path('trucks/<int:pk>/edit/', views.truck_update, name='truck_update'),
    path('trucks/<int:pk>/delete/', views.truck_delete, name='truck_delete'),
    
    # 商品
    path('items/', views.item_list, name='item_list'),
    path('items/new/', views.item_create, name='item_create'),
    path('items/<str:pk>/', views.item_detail, name='item_detail'),
    path('items/<str:pk>/edit/', views.item_update, name='item_update'),
    path('items/<str:pk>/delete/', views.item_delete, name='item_delete'),
    
    # 荷主・配送先
    path('shippers/', views.shipper_list, name='shipper_list'),
    path('shippers/new/', views.shipper_create, name='shipper_create'),
    path('shippers/<int:pk>/', views.shipper_detail, name='shipper_detail'),
    path('shippers/<int:pk>/edit/', views.shipper_update, name='shipper_update'),
    path('shippers/<int:pk>/delete/', views.shipper_delete, name='shipper_delete'),
    path('destinations/', views.destination_list, name='destination_list'),
    path('destinations/new/', views.destination_create, name='destination_create'),
    path('destinations/<int:pk>/', views.destination_detail, name='destination_detail'),
    path('destinations/<int:pk>/edit/', views.destination_update, name='destination_update'),
    path('destinations/<int:pk>/delete/', views.destination_delete, name='destination_delete'),
    
    # レポート
    path('reports/plan/<int:plan_id>/', views.plan_report, name='plan_report'),
    
    # データインポート
    path('import/', views.data_import, name='data_import'),
]
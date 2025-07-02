from django.urls import path
from . import views

app_name = 'delivery'

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('products/', views.ProductListView.as_view(), name='product_list'),
    path('trucks/', views.TruckListView.as_view(), name='truck_list'),
    path('optimize/', views.OptimizeView.as_view(), name='optimize'),
]
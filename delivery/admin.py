from django.contrib import admin
from .models import (
    Item, Part, Shipper, Destination, ShippingOrder, 
    OrderItem, Truck, DeliveryPlan, PlanOrderDetail, PlanItemLoad,
    PalletConfiguration
)


class PartInline(admin.TabularInline):
    model = Part
    extra = 1


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ['item_code', 'name', 'width', 'depth', 'height', 'weight', 'parts_count']
    search_fields = ['item_code', 'name']
    inlines = [PartInline]


@admin.register(Shipper)
class ShipperAdmin(admin.ModelAdmin):
    list_display = ['shipper_code', 'name', 'address', 'contact_phone']
    search_fields = ['shipper_code', 'name']


@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'postal_code', 'latitude', 'longitude']
    search_fields = ['name', 'address', 'postal_code']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1


@admin.register(ShippingOrder)
class ShippingOrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'shipper', 'destination', 'delivery_deadline', 'created_at']
    list_filter = ['delivery_deadline', 'created_at', 'shipper']
    search_fields = ['order_number', 'destination__name']
    inlines = [OrderItemInline]
    date_hierarchy = 'delivery_deadline'


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ['shipping_company', 'truck_class', 'model', 'width', 'depth', 'height', 'payload']
    list_filter = ['shipping_company', 'truck_class']
    search_fields = ['shipping_company', 'model']


class PlanOrderDetailInline(admin.TabularInline):
    model = PlanOrderDetail
    extra = 0


class PlanItemLoadInline(admin.TabularInline):
    model = PlanItemLoad
    extra = 0


@admin.register(DeliveryPlan)
class DeliveryPlanAdmin(admin.ModelAdmin):
    list_display = ['id', 'plan_date', 'truck', 'departure_time', 'total_weight', 'total_volume']
    list_filter = ['plan_date', 'truck__shipping_company']
    date_hierarchy = 'plan_date'
    inlines = [PlanOrderDetailInline, PlanItemLoadInline]


@admin.register(PalletConfiguration)
class PalletConfigurationAdmin(admin.ModelAdmin):
    list_display = ['name', 'width', 'depth', 'max_height', 'max_weight', 'is_default', 'updated_at']
    list_filter = ['is_default', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('基本設定', {
            'fields': ('name', 'is_default')
        }),
        ('パレット仕様', {
            'fields': ('width', 'depth', 'max_height', 'max_weight')
        }),
        ('履歴', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related()
    
    def save_model(self, request, obj, form, change):
        """デフォルト設定の変更を記録"""
        if obj.is_default and not change:
            # 新規作成時にデフォルト設定を作成
            super().save_model(request, obj, form, change)
        elif obj.is_default and change:
            # 既存のデフォルト設定を無効化
            PalletConfiguration.objects.filter(is_default=True).exclude(pk=obj.pk).update(is_default=False)
            super().save_model(request, obj, form, change)
        else:
            super().save_model(request, obj, form, change)
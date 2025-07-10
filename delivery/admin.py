from django.contrib import admin
from .models import (
    Item, Part, Shipper, Destination, ShippingOrder, 
    OrderItem, Truck, DeliveryPlan, PlanOrderDetail, PlanItemLoad
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
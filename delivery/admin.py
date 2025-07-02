from django.contrib import admin
from .models import Shipper, Product, Truck, DeliveryPlan, TruckAssignment, ProductAssignment


@admin.register(Shipper)
class ShipperAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
    search_fields = ['name']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'shipper', 'destination_address', 'delivery_deadline', 'weight', 'volume']
    list_filter = ['shipper', 'delivery_deadline']
    search_fields = ['name', 'destination_address']
    
    def volume(self, obj):
        return f"{obj.volume:.0f} cm³"
    volume.short_description = '体積'


@admin.register(Truck)
class TruckAdmin(admin.ModelAdmin):
    list_display = ['name', 'bed_area', 'max_weight', 'created_at']
    search_fields = ['name']
    
    def bed_area(self, obj):
        return f"{obj.bed_area:.0f} cm²"
    bed_area.short_description = '荷台面積'


@admin.register(DeliveryPlan)
class DeliveryPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'dispatch_time', 'created_at']
    list_filter = ['dispatch_time']
    search_fields = ['name']


class ProductAssignmentInline(admin.TabularInline):
    model = ProductAssignment
    extra = 0


@admin.register(TruckAssignment)
class TruckAssignmentAdmin(admin.ModelAdmin):
    list_display = ['delivery_plan', 'truck', 'total_distance', 'estimated_time']
    list_filter = ['delivery_plan', 'truck']
    inlines = [ProductAssignmentInline]
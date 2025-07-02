from django.db import models
from django.utils import timezone


class Shipper(models.Model):
    """荷主情報"""
    name = models.CharField(max_length=100, verbose_name='荷主名')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '荷主'
        verbose_name_plural = '荷主'
    
    def __str__(self):
        return self.name


class Product(models.Model):
    """商品情報"""
    shipper = models.ForeignKey(Shipper, on_delete=models.CASCADE, related_name='products', verbose_name='荷主')
    name = models.CharField(max_length=200, verbose_name='商品名')
    width = models.FloatField(verbose_name='幅(cm)')
    height = models.FloatField(verbose_name='高さ(cm)')
    depth = models.FloatField(verbose_name='奥行き(cm)')
    weight = models.FloatField(verbose_name='重量(kg)')
    destination_address = models.CharField(max_length=500, verbose_name='配送先住所')
    delivery_deadline = models.DateTimeField(verbose_name='配送期限')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '商品'
        verbose_name_plural = '商品'
    
    def __str__(self):
        return f"{self.name} - {self.destination_address}"
    
    @property
    def volume(self):
        """体積(cm³)"""
        return self.width * self.height * self.depth
    
    @property
    def area(self):
        """底面積(cm²)"""
        return self.width * self.depth


class Truck(models.Model):
    """トラック情報"""
    name = models.CharField(max_length=100, verbose_name='トラック名/番号')
    bed_width = models.FloatField(verbose_name='荷台幅(cm)')
    bed_depth = models.FloatField(verbose_name='荷台奥行き(cm)')
    max_weight = models.FloatField(verbose_name='最大積載量(kg)')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'トラック'
        verbose_name_plural = 'トラック'
    
    def __str__(self):
        return self.name
    
    @property
    def bed_area(self):
        """荷台面積(cm²)"""
        return self.bed_width * self.bed_depth


class DeliveryPlan(models.Model):
    """配送計画"""
    name = models.CharField(max_length=200, verbose_name='計画名')
    dispatch_time = models.DateTimeField(verbose_name='発送時刻')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = '配送計画'
        verbose_name_plural = '配送計画'
    
    def __str__(self):
        return f"{self.name} - {self.dispatch_time}"


class TruckAssignment(models.Model):
    """トラック割り当て"""
    delivery_plan = models.ForeignKey(DeliveryPlan, on_delete=models.CASCADE, related_name='truck_assignments')
    truck = models.ForeignKey(Truck, on_delete=models.CASCADE)
    route_order = models.JSONField(default=list, verbose_name='配送ルート順序')
    total_distance = models.FloatField(default=0, verbose_name='総走行距離(km)')
    estimated_time = models.FloatField(default=0, verbose_name='推定所要時間(分)')
    
    class Meta:
        verbose_name = 'トラック割り当て'
        verbose_name_plural = 'トラック割り当て'
        unique_together = ['delivery_plan', 'truck']
    
    def __str__(self):
        return f"{self.delivery_plan.name} - {self.truck.name}"


class ProductAssignment(models.Model):
    """商品割り当て"""
    truck_assignment = models.ForeignKey(TruckAssignment, on_delete=models.CASCADE, related_name='product_assignments')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    x_position = models.FloatField(verbose_name='X座標(cm)')
    y_position = models.FloatField(verbose_name='Y座標(cm)')
    
    class Meta:
        verbose_name = '商品割り当て'
        verbose_name_plural = '商品割り当て'
        unique_together = ['truck_assignment', 'product']
    
    def __str__(self):
        return f"{self.product.name} in {self.truck_assignment.truck.name}"
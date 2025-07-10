from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Item(models.Model):
    """製品テーブル"""
    item_code = models.CharField('品目コード', max_length=100, primary_key=True)
    name = models.CharField('製品名', max_length=100)
    width = models.IntegerField('幅(cm)', null=True, blank=True, validators=[MinValueValidator(0)])
    depth = models.IntegerField('奥行(cm)', null=True, blank=True, validators=[MinValueValidator(0)])
    height = models.IntegerField('高さ(cm)', null=True, blank=True, validators=[MinValueValidator(0)])
    weight = models.FloatField('質量(kg)', null=True, blank=True, validators=[MinValueValidator(0)])
    parts_count = models.IntegerField('セット品PCS数', default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        verbose_name = '製品'
        verbose_name_plural = '製品'
        
    def __str__(self):
        return f"{self.item_code} - {self.name}"
    
    @property
    def volume(self):
        """体積を計算（cm³）"""
        if self.width and self.depth and self.height:
            return self.width * self.depth * self.height
        return 0


class Part(models.Model):
    """セット品(部品)テーブル"""
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='parts')
    parts_code = models.CharField('部品コード', max_length=100)
    width = models.IntegerField('幅(cm)', validators=[MinValueValidator(0)])
    depth = models.IntegerField('奥行(cm)', validators=[MinValueValidator(0)])
    height = models.IntegerField('高さ(cm)', validators=[MinValueValidator(0)])
    weight = models.FloatField('質量(kg)', validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = '部品'
        verbose_name_plural = '部品'
        unique_together = ['item', 'parts_code']
        
    def __str__(self):
        return f"{self.item.item_code} - {self.parts_code}"


class Shipper(models.Model):
    """荷主テーブル"""
    shipper_code = models.CharField('荷主コード', max_length=100, unique=True)
    name = models.CharField('荷主名', max_length=200)
    address = models.CharField('住所', max_length=500)
    contact_phone = models.CharField('連絡先電話', max_length=20, blank=True)
    contact_email = models.EmailField('連絡先メール', blank=True)
    
    class Meta:
        verbose_name = '荷主'
        verbose_name_plural = '荷主'
        
    def __str__(self):
        return f"{self.shipper_code} - {self.name}"


class Destination(models.Model):
    """配送先テーブル"""
    name = models.CharField('配送先名', max_length=200)
    address = models.CharField('住所（町丁目まで）', max_length=500)
    postal_code = models.CharField('郵便番号', max_length=10, blank=True)
    latitude = models.DecimalField('緯度', max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField('経度', max_digits=9, decimal_places=6, null=True, blank=True)
    contact_phone = models.CharField('連絡先電話', max_length=20, blank=True)
    
    class Meta:
        verbose_name = '配送先'
        verbose_name_plural = '配送先'
        
    def __str__(self):
        return f"{self.name} - {self.address}"


class ShippingOrder(models.Model):
    """出荷依頼テーブル"""
    order_number = models.CharField('出荷依頼番号', max_length=100, unique=True)
    shipper = models.ForeignKey(Shipper, on_delete=models.PROTECT, verbose_name='荷主')
    destination = models.ForeignKey(Destination, on_delete=models.PROTECT, verbose_name='配送先')
    delivery_deadline = models.DateField('お届け日')
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = '出荷依頼'
        verbose_name_plural = '出荷依頼'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"{self.order_number} - {self.destination.name}"


class OrderItem(models.Model):
    """出荷商品テーブル"""
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.CASCADE, related_name='order_items')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name='品目')
    quantity = models.IntegerField('数量', default=1, validators=[MinValueValidator(1)])
    
    class Meta:
        verbose_name = '出荷商品'
        verbose_name_plural = '出荷商品'
        
    def __str__(self):
        return f"{self.shipping_order.order_number} - {self.item.name} x {self.quantity}"


class Truck(models.Model):
    """トラックテーブル"""
    width = models.IntegerField('荷台幅(cm)', default=0, validators=[MinValueValidator(0)])
    depth = models.IntegerField('荷台奥行(cm)', default=0, validators=[MinValueValidator(0)])
    height = models.IntegerField('荷台高さ(cm)', default=0, validators=[MinValueValidator(0)])
    payload = models.IntegerField('最大積載量(kg)', default=0, validators=[MinValueValidator(0)])
    shipping_company = models.CharField('運送会社名', max_length=256, blank=True)
    truck_class = models.CharField('車格', max_length=100, blank=True)
    model = models.CharField('車種', max_length=100, blank=True)
    
    class Meta:
        verbose_name = 'トラック'
        verbose_name_plural = 'トラック'
        
    def __str__(self):
        return f"{self.shipping_company} {self.truck_class} - {self.model}"
    
    @property
    def floor_area(self):
        """荷台面積（cm²）"""
        return self.width * self.depth
    
    @property
    def volume(self):
        """荷台容積（cm³）"""
        return self.width * self.depth * self.height


class DeliveryPlan(models.Model):
    """配送計画テーブル"""
    plan_date = models.DateField('配送日')
    truck = models.ForeignKey(Truck, on_delete=models.PROTECT, verbose_name='トラック')
    departure_time = models.DateTimeField('出発予定時刻')
    total_weight = models.FloatField('積載合計重量(kg)', validators=[MinValueValidator(0)])
    total_volume = models.IntegerField('積載合計体積(cm³)', validators=[MinValueValidator(0)])
    route_distance_km = models.FloatField('想定走行距離(km)', null=True, blank=True, validators=[MinValueValidator(0)])
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '配送計画'
        verbose_name_plural = '配送計画'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"計画{self.id} - {self.plan_date} {self.truck}"


class PlanOrderDetail(models.Model):
    """配送計画明細テーブル"""
    plan = models.ForeignKey(DeliveryPlan, on_delete=models.CASCADE, related_name='order_details')
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.PROTECT, verbose_name='出荷依頼')
    delivery_sequence = models.IntegerField('配送順序', validators=[MinValueValidator(1)])
    estimated_arrival = models.DateTimeField('到着予定時刻')
    travel_time_minutes = models.IntegerField('移動時間(分)', validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = '配送計画明細'
        verbose_name_plural = '配送計画明細'
        unique_together = ['plan', 'shipping_order']
        ordering = ['delivery_sequence']
        
    def __str__(self):
        return f"{self.plan} - 順序{self.delivery_sequence}: {self.shipping_order}"


class PlanItemLoad(models.Model):
    """積載商品テーブル"""
    plan = models.ForeignKey(DeliveryPlan, on_delete=models.CASCADE, related_name='item_loads')
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.PROTECT, verbose_name='出荷依頼')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name='品目')
    quantity = models.IntegerField('個数', validators=[MinValueValidator(1)])
    position_x = models.IntegerField('積載位置X座標(cm)', validators=[MinValueValidator(0)])
    position_y = models.IntegerField('積載位置Y座標(cm)', validators=[MinValueValidator(0)])
    rotation = models.IntegerField('回転角度', default=0, choices=[(0, '0°'), (90, '90°'), (180, '180°'), (270, '270°')])
    
    class Meta:
        verbose_name = '積載商品'
        verbose_name_plural = '積載商品'
        
    def __str__(self):
        return f"{self.plan} - {self.item.name} x {self.quantity}"
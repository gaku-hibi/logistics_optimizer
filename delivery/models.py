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


class PalletizePlan(models.Model):
    """パレタイズ設計結果"""
    delivery_date = models.DateField('配送日')
    total_items = models.IntegerField('総商品数', validators=[MinValueValidator(0)])
    total_pallets = models.IntegerField('パレット数', validators=[MinValueValidator(0)])
    total_loose_items = models.IntegerField('バラ積み商品数', validators=[MinValueValidator(0)])
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = 'パレタイズ設計'
        verbose_name_plural = 'パレタイズ設計'
        ordering = ['-created_at']
        
    def __str__(self):
        return f"パレタイズ設計 {self.delivery_date} - {self.total_pallets}パレット"


class PalletDetail(models.Model):
    """パレット詳細"""
    palletize_plan = models.ForeignKey(PalletizePlan, on_delete=models.CASCADE, related_name='pallets')
    pallet_number = models.IntegerField('パレット番号', validators=[MinValueValidator(1)])
    total_weight = models.FloatField('総重量(kg)', validators=[MinValueValidator(0)])
    total_volume = models.IntegerField('総体積(cm³)', validators=[MinValueValidator(0)])
    utilization = models.FloatField('積載率(%)', validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = 'パレット詳細'
        verbose_name_plural = 'パレット詳細'
        ordering = ['pallet_number']
        unique_together = ['palletize_plan', 'pallet_number']
        
    def __str__(self):
        return f"{self.palletize_plan} - パレット#{self.pallet_number}"
    
    def get_related_order_numbers(self):
        """関連する出荷依頼番号のリストを取得"""
        return list(self.items.values_list('shipping_order__order_number', flat=True).distinct())
    
    def get_item_summary(self):
        """商品の集計情報を取得（上位3種類）"""
        from collections import defaultdict
        
        item_counts = defaultdict(int)
        item_info = {}
        
        for pallet_item in self.items.all():
            if pallet_item.part:
                item_code = pallet_item.part.parts_code
                item_name = f"{pallet_item.item.name}（部品）"
            else:
                item_code = pallet_item.item.item_code
                item_name = pallet_item.item.name
            
            item_counts[item_code] += 1
            if item_code not in item_info:
                item_info[item_code] = {
                    'item_code': item_code,
                    'item_name': item_name,
                    'quantity': 0
                }
        
        # 件数を更新
        for item_code, count in item_counts.items():
            item_info[item_code]['quantity'] = count
        
        # 数量の多い順に並び替えて上位3つを返す
        sorted_items = sorted(item_info.values(), key=lambda x: x['quantity'], reverse=True)
        return sorted_items[:3]


class PalletItem(models.Model):
    """パレット積載商品"""
    pallet = models.ForeignKey(PalletDetail, on_delete=models.CASCADE, related_name='items')
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.PROTECT, verbose_name='出荷依頼')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name='品目')
    part = models.ForeignKey(Part, on_delete=models.PROTECT, null=True, blank=True, verbose_name='部品')
    position_x = models.IntegerField('X座標(cm)', validators=[MinValueValidator(0)])
    position_y = models.IntegerField('Y座標(cm)', validators=[MinValueValidator(0)])
    position_z = models.IntegerField('Z座標(cm)', validators=[MinValueValidator(0)])
    width = models.IntegerField('幅(cm)', validators=[MinValueValidator(0)])
    depth = models.IntegerField('奥行(cm)', validators=[MinValueValidator(0)])
    height = models.IntegerField('高さ(cm)', validators=[MinValueValidator(0)])
    weight = models.FloatField('重量(kg)', validators=[MinValueValidator(0)])
    
    class Meta:
        verbose_name = 'パレット積載商品'
        verbose_name_plural = 'パレット積載商品'
        
    def __str__(self):
        if self.part:
            return f"{self.pallet} - {self.part.parts_code}"
        return f"{self.pallet} - {self.item.item_code}"


class LooseItem(models.Model):
    """バラ積み商品"""
    palletize_plan = models.ForeignKey(PalletizePlan, on_delete=models.CASCADE, related_name='loose_items')
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.PROTECT, verbose_name='出荷依頼')
    item = models.ForeignKey(Item, on_delete=models.PROTECT, verbose_name='品目')
    width = models.IntegerField('幅(cm)', validators=[MinValueValidator(0)])
    depth = models.IntegerField('奥行(cm)', validators=[MinValueValidator(0)])
    height = models.IntegerField('高さ(cm)', validators=[MinValueValidator(0)])
    weight = models.FloatField('重量(kg)', validators=[MinValueValidator(0)])
    reason = models.CharField('理由', max_length=100)
    
    class Meta:
        verbose_name = 'バラ積み商品'
        verbose_name_plural = 'バラ積み商品'
        
    def __str__(self):
        return f"{self.palletize_plan} - {self.item.name} (バラ積み)"


class PalletConfiguration(models.Model):
    """パレット設定"""
    name = models.CharField('設定名', max_length=100, unique=True)
    width = models.IntegerField('パレット幅(cm)', default=100, validators=[MinValueValidator(1)])
    depth = models.IntegerField('パレット奥行(cm)', default=100, validators=[MinValueValidator(1)])
    max_height = models.IntegerField('最大積み上げ高さ(cm)', default=80, validators=[MinValueValidator(1)])
    max_weight = models.FloatField('最大積載重量(kg)', default=100.0, validators=[MinValueValidator(0.1)])
    is_default = models.BooleanField('デフォルト設定', default=False)
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)
    
    class Meta:
        verbose_name = 'パレット設定'
        verbose_name_plural = 'パレット設定'
        ordering = ['-is_default', 'name']
        
    def __str__(self):
        default_text = " (デフォルト)" if self.is_default else ""
        return f"{self.name}{default_text} - {self.width}×{self.depth}×{self.max_height}cm, {self.max_weight}kg"
    
    def save(self, *args, **kwargs):
        """デフォルト設定は1つのみ許可"""
        if self.is_default:
            # 他のデフォルト設定を無効化
            PalletConfiguration.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)
    
    @classmethod
    def get_default(cls):
        """デフォルト設定を取得"""
        try:
            return cls.objects.get(is_default=True)
        except cls.DoesNotExist:
            # デフォルト設定がない場合は作成
            return cls.objects.create(
                name="標準パレット",
                width=100,
                depth=100,
                max_height=80,
                max_weight=100.0,
                is_default=True
            )
    
    @property
    def pallet_area(self):
        """パレット面積（cm²）"""
        return self.width * self.depth
    
    @property
    def max_volume(self):
        """最大体積（cm³）"""
        return self.width * self.depth * self.max_height


class UnifiedPallet(models.Model):
    """統一パレットテーブル（パレタイズされたパレットと疑似パレット）"""
    PALLET_TYPE_CHOICES = [
        ('REAL', 'パレタイズされたパレット'),
        ('VIRTUAL', '疑似パレット（バラ積み）'),
    ]
    
    pallet_type = models.CharField('パレットタイプ', max_length=20, choices=PALLET_TYPE_CHOICES)
    delivery_date = models.DateField('配送日')
    width = models.IntegerField('パレット幅(cm)', validators=[MinValueValidator(1)])
    depth = models.IntegerField('パレット奥行(cm)', validators=[MinValueValidator(1)])
    height = models.IntegerField('パレット高さ(cm)', validators=[MinValueValidator(1)])
    weight = models.FloatField('パレット重量(kg)', validators=[MinValueValidator(0)])
    volume = models.IntegerField('パレット体積(cm³)', validators=[MinValueValidator(1)])
    shipping_order = models.ForeignKey(ShippingOrder, on_delete=models.PROTECT, verbose_name='出荷依頼', null=True, blank=True)
    # 複数の注文を含むパレットのため、多対多関係を追加
    related_orders = models.ManyToManyField(ShippingOrder, related_name='unified_pallets', verbose_name='関連する出荷依頼', blank=True)
    
    # REALパレットの場合
    pallet_detail = models.ForeignKey(PalletDetail, on_delete=models.CASCADE, null=True, blank=True, verbose_name='パレット詳細')
    
    # VIRTUALパレットの場合
    item = models.ForeignKey(Item, on_delete=models.PROTECT, null=True, blank=True, verbose_name='品目')
    item_quantity = models.IntegerField('商品数量', null=True, blank=True, validators=[MinValueValidator(1)])
    
    created_at = models.DateTimeField('作成日時', auto_now_add=True)
    
    class Meta:
        verbose_name = '統一パレット'
        verbose_name_plural = '統一パレット'
        ordering = ['-created_at']
        
    def __str__(self):
        if self.pallet_type == 'REAL':
            return f"パレット#{self.pallet_detail.pallet_number} - {self.shipping_order.order_number}"
        else:
            return f"疑似パレット({self.item.name}) - {self.shipping_order.order_number}"
    
    def clean(self):
        """バリデーション"""
        from django.core.exceptions import ValidationError
        
        if self.pallet_type == 'REAL':
            if not self.pallet_detail:
                raise ValidationError('REALパレットはパレット詳細が必要です')
            if self.item or self.item_quantity:
                raise ValidationError('REALパレットには品目情報は不要です')
        elif self.pallet_type == 'VIRTUAL':
            if not self.item or not self.item_quantity:
                raise ValidationError('VIRTUALパレットは品目と数量が必要です')
            if self.pallet_detail:
                raise ValidationError('VIRTUALパレットにはパレット詳細は不要です')
    
    @property
    def display_name(self):
        """表示名"""
        if self.pallet_type == 'REAL':
            return f"パレット#{self.pallet_detail.pallet_number}"
        else:
            return f"{self.item.name} x{self.item_quantity}"


class LoadPallet(models.Model):
    """積載パレットテーブル（旧PlanItemLoadsの置き換え）"""
    plan = models.ForeignKey(DeliveryPlan, on_delete=models.CASCADE, related_name='load_pallets')
    pallet = models.ForeignKey(UnifiedPallet, on_delete=models.PROTECT, verbose_name='パレット')
    position_x = models.IntegerField('積載位置X座標(cm)', validators=[MinValueValidator(0)])
    position_y = models.IntegerField('積載位置Y座標(cm)', validators=[MinValueValidator(0)])
    rotation = models.IntegerField('回転角度', default=0, choices=[(0, '0°'), (90, '90°'), (180, '180°'), (270, '270°')])
    load_sequence = models.IntegerField('積み込み順序', validators=[MinValueValidator(1)])
    
    class Meta:
        verbose_name = '積載パレット'
        verbose_name_plural = '積載パレット'
        ordering = ['load_sequence']
        
    def __str__(self):
        return f"{self.plan} - {self.pallet.display_name}"


class PalletLoadHistory(models.Model):
    """パレット積載履歴テーブル"""
    STATUS_CHOICES = [
        ('ALLOCATED', '割り当て済み'),
        ('USED', '使用中'),
        ('COMPLETED', '完了'),
    ]
    
    pallet = models.ForeignKey(UnifiedPallet, on_delete=models.CASCADE, related_name='load_history')
    plan = models.ForeignKey(DeliveryPlan, on_delete=models.CASCADE, verbose_name='配送計画')
    allocated_at = models.DateTimeField('割り当て日時', auto_now_add=True)
    status = models.CharField('ステータス', max_length=20, choices=STATUS_CHOICES, default='ALLOCATED')
    
    class Meta:
        verbose_name = 'パレット積載履歴'
        verbose_name_plural = 'パレット積載履歴'
        ordering = ['-allocated_at']
        unique_together = ['pallet', 'plan']
        
    def __str__(self):
        return f"{self.pallet.display_name} - {self.plan} ({self.get_status_display()})"
"""
物流配送最適化アルゴリズム

パレタイズ、2Dビンパッキング、配送ルート最適化を実装
"""

import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
from django.db import transaction

from .models import (
    ShippingOrder, OrderItem, Truck, DeliveryPlan, 
    PlanOrderDetail, PlanItemLoad, Item
)


@dataclass
class Box:
    """箱（商品）を表すクラス"""
    width: int
    depth: int
    height: int
    weight: float
    item_code: str
    quantity: int = 1
    x: int = 0  # パレット内での位置
    y: int = 0
    z: int = 0  # 高さ方向の位置


@dataclass
class Pallet:
    """パレットを表すクラス"""
    width: int = 110  # 標準パレット 1.1m
    depth: int = 110
    height: int = 150  # 積み上げ高さ1.5m
    max_weight: float = 1000
    boxes: List[Box] = None
    current_height: int = 0  # 現在の積み上げ高さ
    
    def __post_init__(self):
        if self.boxes is None:
            self.boxes = []
    
    def get_total_weight(self) -> float:
        """パレット上の総重量を取得"""
        return sum(b.weight * b.quantity for b in self.boxes)
    
    def get_used_volume(self) -> int:
        """使用済み体積を取得"""
        return sum(b.width * b.depth * b.height * b.quantity for b in self.boxes)


@dataclass
class Position:
    """位置を表すクラス"""
    x: int
    y: int
    width: int
    depth: int
    rotation: int = 0


class PalletOptimizer:
    """パレタイズ最適化クラス（3D配置対応）"""
    
    def __init__(self):
        self.pallet_width = 110  # cm
        self.pallet_depth = 110  # cm
        self.max_height = 150    # cm
        self.max_weight = 1000   # kg
    
    def can_palletize(self, box: Box) -> bool:
        """商品がパレタイズ可能かチェック"""
        # 回転も考慮して、どちらかの向きで収まるかチェック
        fits_normal = (box.width <= self.pallet_width and box.depth <= self.pallet_depth)
        fits_rotated = (box.depth <= self.pallet_width and box.width <= self.pallet_depth)
        return (fits_normal or fits_rotated) and box.height <= self.max_height
    
    def pack_pallet(self, boxes: List[Box]) -> Tuple[List[Pallet], List[Box]]:
        """箱をパレットに詰める（3D First Fit Decreasing）"""
        pallets = []
        remaining_boxes = []
        
        # 体積順でソート（大きい順）- より効率的なパッキングのため
        sorted_boxes = sorted(boxes, key=lambda b: b.width * b.depth * b.height, reverse=True)
        
        for box in sorted_boxes:
            if not self.can_palletize(box):
                remaining_boxes.append(box)
                continue
            
            placed = False
            
            # 既存パレットに配置可能かチェック
            for pallet in pallets:
                position = self._find_position_on_pallet(pallet, box)
                if position:
                    box.x, box.y, box.z = position
                    pallet.boxes.append(box)
                    # パレットの現在の高さを更新
                    pallet.current_height = max(pallet.current_height, box.z + box.height)
                    placed = True
                    break
            
            # 新しいパレットが必要
            if not placed:
                new_pallet = Pallet()
                box.x, box.y, box.z = 0, 0, 0
                new_pallet.boxes.append(box)
                new_pallet.current_height = box.height
                pallets.append(new_pallet)
        
        return pallets, remaining_boxes
    
    def _find_position_on_pallet(self, pallet: Pallet, box: Box) -> Optional[Tuple[int, int, int]]:
        """パレット上で箱を配置可能な位置を探す（3D）"""
        # 重量チェック
        if pallet.get_total_weight() + box.weight * box.quantity > self.max_weight:
            return None
        
        # 高さチェック
        if pallet.current_height + box.height > self.max_height:
            return None
        
        # 可能な配置位置を探す
        possible_positions = []
        
        # 床面（z=0）での配置を試す
        for y in range(0, self.pallet_depth - box.depth + 1, 5):  # 5cm刻み
            for x in range(0, self.pallet_width - box.width + 1, 5):
                if self._can_place_at_3d(pallet, x, y, 0, box):
                    possible_positions.append((x, y, 0))
        
        # 既存の箱の上に配置を試す
        for existing_box in pallet.boxes:
            # 既存の箱の上面の位置
            top_z = existing_box.z + existing_box.height
            
            # 高さ制限チェック
            if top_z + box.height > self.max_height:
                continue
            
            # 既存の箱の上での配置可能位置を探す
            for y in range(existing_box.y, min(existing_box.y + existing_box.depth, self.pallet_depth - box.depth + 1)):
                for x in range(existing_box.x, min(existing_box.x + existing_box.width, self.pallet_width - box.width + 1)):
                    if self._can_place_at_3d(pallet, x, y, top_z, box):
                        possible_positions.append((x, y, top_z))
        
        # 最も低い位置を選択（安定性のため）
        if possible_positions:
            return min(possible_positions, key=lambda p: p[2])
        
        return None
    
    def _can_place_at_3d(self, pallet: Pallet, x: int, y: int, z: int, box: Box) -> bool:
        """3D空間で指定位置に配置可能かチェック"""
        # 境界チェック
        if x + box.width > self.pallet_width or y + box.depth > self.pallet_depth:
            return False
        
        # 既存の箱との衝突チェック
        for existing_box in pallet.boxes:
            if self._boxes_overlap_3d(
                x, y, z, x + box.width, y + box.depth, z + box.height,
                existing_box.x, existing_box.y, existing_box.z,
                existing_box.x + existing_box.width,
                existing_box.y + existing_box.depth,
                existing_box.z + existing_box.height
            ):
                return False
        
        # 下に支えがあるかチェック（z > 0の場合）
        if z > 0:
            support_area = 0
            box_area = box.width * box.depth
            
            for existing_box in pallet.boxes:
                # 既存の箱の上面がこの箱の底面と接する場合
                if existing_box.z + existing_box.height == z:
                    # 重なり部分の面積を計算
                    overlap_x1 = max(x, existing_box.x)
                    overlap_y1 = max(y, existing_box.y)
                    overlap_x2 = min(x + box.width, existing_box.x + existing_box.width)
                    overlap_y2 = min(y + box.depth, existing_box.y + existing_box.depth)
                    
                    if overlap_x1 < overlap_x2 and overlap_y1 < overlap_y2:
                        support_area += (overlap_x2 - overlap_x1) * (overlap_y2 - overlap_y1)
            
            # 少なくとも70%の面積が支えられている必要がある
            if support_area < box_area * 0.7:
                return False
        
        return True
    
    def _boxes_overlap_3d(self, x1: int, y1: int, z1: int, x2: int, y2: int, z2: int,
                          x3: int, y3: int, z3: int, x4: int, y4: int, z4: int) -> bool:
        """3D空間での箱の重複チェック"""
        return not (x2 <= x3 or x4 <= x1 or y2 <= y3 or y4 <= y1 or z2 <= z3 or z4 <= z1)


class BinPacking2D:
    """2Dビンパッキング（トラック積載最適化）"""
    
    def __init__(self, truck_width: int, truck_depth: int):
        self.truck_width = truck_width
        self.truck_depth = truck_depth
        self.placed_items = []
    
    def pack(self, items: List[Box]) -> List[Position]:
        """Bottom-Left Fill アルゴリズムで配置"""
        positions = []
        
        # アイテムを面積の大きい順にソート
        sorted_items = sorted(items, key=lambda x: x.width * x.depth, reverse=True)
        
        for item in sorted_items:
            position = self._find_position(item)
            if position:
                positions.append(position)
                self.placed_items.append((item, position))
        
        return positions
    
    def _find_position(self, item: Box) -> Optional[Position]:
        """アイテムを配置可能な位置を探す"""
        # 回転も考慮
        orientations = [
            (item.width, item.depth, 0),
            (item.depth, item.width, 90)
        ]
        
        for width, depth, rotation in orientations:
            for y in range(0, self.truck_depth - depth + 1, 10):  # 10cm刻み
                for x in range(0, self.truck_width - width + 1, 10):
                    if self._can_place_at(x, y, width, depth):
                        return Position(x, y, width, depth, rotation)
        
        return None
    
    def _can_place_at(self, x: int, y: int, width: int, depth: int) -> bool:
        """指定位置に配置可能かチェック"""
        for item, pos in self.placed_items:
            if self._rectangles_overlap(
                x, y, x + width, y + depth,
                pos.x, pos.y, pos.x + pos.width, pos.y + pos.depth
            ):
                return False
        return True
    
    def _rectangles_overlap(self, x1: int, y1: int, x2: int, y2: int,
                           x3: int, y3: int, x4: int, y4: int) -> bool:
        """矩形の重複チェック"""
        return not (x2 <= x3 or x4 <= x1 or y2 <= y3 or y4 <= y1)


class RouteOptimizer:
    """配送ルート最適化（Nearest Neighbor）"""
    
    def __init__(self):
        self.depot = (35.6762, 139.6503)  # 東京駅を配送拠点とする
    
    def optimize_route(self, destinations: List[Tuple[float, float]]) -> List[int]:
        """最近傍法でルートを最適化"""
        if not destinations:
            return []
        
        n = len(destinations)
        visited = [False] * n
        route = []
        current = 0  # 最初の配送先から開始
        
        # 距離行列を計算
        distances = self._calculate_distance_matrix(destinations)
        
        route.append(current)
        visited[current] = True
        
        for _ in range(n - 1):
            nearest = -1
            min_distance = float('inf')
            
            for i in range(n):
                if not visited[i] and distances[current][i] < min_distance:
                    min_distance = distances[current][i]
                    nearest = i
            
            if nearest != -1:
                route.append(nearest)
                visited[nearest] = True
                current = nearest
        
        return route
    
    def _calculate_distance_matrix(self, destinations: List[Tuple[float, float]]) -> List[List[float]]:
        """距離行列を計算（ハーバサイン距離）"""
        n = len(destinations)
        distances = [[0.0] * n for _ in range(n)]
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    distances[i][j] = self._haversine_distance(
                        destinations[i], destinations[j]
                    )
        
        return distances
    
    def _haversine_distance(self, coord1: Tuple[float, float], 
                           coord2: Tuple[float, float]) -> float:
        """ハーバサイン距離計算（km）"""
        lat1, lon1 = coord1
        lat2, lon2 = coord2
        
        R = 6371  # 地球の半径（km）
        
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        
        a = (math.sin(dlat/2) * math.sin(dlat/2) + 
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * 
             math.sin(dlon/2) * math.sin(dlon/2))
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c


class DeliveryOptimizer:
    """配送最適化メインクラス"""
    
    def __init__(self):
        self.pallet_optimizer = PalletOptimizer()
        self.route_optimizer = RouteOptimizer()
    
    def optimize(self, orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """配送最適化を実行"""
        plans = []
        
        try:
            with transaction.atomic():
                # 1. 注文を地域別にグループ化
                grouped_orders = self._group_orders_by_region(orders)
                
                for region, region_orders in grouped_orders.items():
                    # 2. 商品をパレタイズ
                    pallets, loose_items = self._palletize_orders(region_orders)
                    
                    # 3. トラックに積載
                    truck_plans = self._pack_trucks(pallets, loose_items, region_orders, target_date)
                    
                    plans.extend(truck_plans)
                
        except Exception as e:
            print(f"最適化エラー: {e}")
            return []
        
        return plans
    
    def _group_orders_by_region(self, orders: List[ShippingOrder]) -> Dict[str, List[ShippingOrder]]:
        """注文を地域別にグループ化"""
        groups = {}
        
        for order in orders:
            # 住所から市区町村を抽出（簡易版）
            address = order.destination.address
            region = self._extract_region(address)
            
            if region not in groups:
                groups[region] = []
            groups[region].append(order)
        
        return groups
    
    def _extract_region(self, address: str) -> str:
        """住所から地域を抽出"""
        # 簡易的な実装：最初の市区町村を抽出
        if '東京都' in address:
            if '区' in address:
                return '東京23区'
            else:
                return '東京都下'
        elif '神奈川県' in address:
            return '神奈川県'
        elif '埼玉県' in address:
            return '埼玉県'
        elif '千葉県' in address:
            return '千葉県'
        else:
            return 'その他'
    
    def _palletize_orders(self, orders: List[ShippingOrder]) -> Tuple[List[Pallet], List[Box]]:
        """注文商品をパレタイズ"""
        all_boxes = []
        
        # 注文から箱リストを作成（個別の商品単位で）
        for order in orders:
            for order_item in order.order_items.all():
                item = order_item.item
                if item.width and item.depth and item.height and item.weight:
                    # 各商品を個別の箱として作成（quantityの数だけ）
                    for _ in range(order_item.quantity):
                        box = Box(
                            width=item.width,
                            depth=item.depth,
                            height=item.height,
                            weight=item.weight,
                            item_code=item.item_code,
                            quantity=1  # 各箱は個別に扱う
                        )
                        all_boxes.append(box)
        
        return self.pallet_optimizer.pack_pallet(all_boxes)
    
    def _pack_trucks(self, pallets: List[Pallet], loose_items: List[Box], 
                    orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """トラックに積載して配送計画を作成（2D配置のみ、段積み禁止）"""
        plans = []
        trucks = Truck.objects.filter(width__gt=0, depth__gt=0).order_by('-payload')
        
        if not trucks:
            return plans
        
        # 全アイテムを収集（パレットとバラ積み商品）
        all_items = []
        
        # パレットを箱として扱う（3Dパレット内は段積み済み）
        for pallet in pallets:
            pallet_box = Box(
                width=pallet.width,
                depth=pallet.depth,
                height=pallet.current_height,  # 実際の積み上げ高さを使用
                weight=pallet.get_total_weight(),
                item_code='PALLET',
                quantity=1
            )
            all_items.append(pallet_box)
        
        # バラ積み商品を追加
        all_items.extend(loose_items)
        
        # トラックに2D配置で詰込み（段積み禁止）
        remaining_items = all_items.copy()
        
        for truck in trucks:
            if not remaining_items:
                break
            
            # 重量制限チェック
            truck_capacity = truck.payload
            current_weight = 0
            truck_items = []
            
            # 重量制限内でアイテムを選択
            for item in remaining_items.copy():
                if current_weight + (item.weight * item.quantity) <= truck_capacity:
                    truck_items.append(item)
                    current_weight += item.weight * item.quantity
                    remaining_items.remove(item)
            
            if truck_items:
                # 2D配置でパッキング
                packer = BinPacking2D(truck.width, truck.depth)
                positions = packer.pack(truck_items)
                
                if positions:
                    plan = self._create_delivery_plan(
                        truck, orders, target_date, truck_items, positions
                    )
                    plans.append(plan)
                    
                    # 配置されなかったアイテムを戻す
                    placed_items = [item for item, _ in packer.placed_items]
                    not_placed = [item for item in truck_items if item not in placed_items]
                    remaining_items.extend(not_placed)
        
        return plans
    
    def _create_delivery_plan(self, truck: Truck, orders: List[ShippingOrder], 
                             target_date, items: List[Box], positions: List[Position]) -> DeliveryPlan:
        """配送計画を作成"""
        
        # 配送ルートを最適化
        destinations = []
        for order in orders:
            if order.destination.latitude and order.destination.longitude:
                destinations.append((
                    float(order.destination.latitude), 
                    float(order.destination.longitude)
                ))
        
        if destinations:
            route_indices = self.route_optimizer.optimize_route(destinations)
        else:
            route_indices = list(range(len(orders)))
        
        # 重量・体積計算
        total_weight = sum(item.weight * item.quantity for item in items)
        total_volume = sum(item.width * item.depth * item.height * item.quantity for item in items)
        
        # 出発時刻計算（配送時間を逆算）
        departure_time = datetime.combine(target_date, datetime.min.time().replace(hour=8))
        
        # 配送計画作成
        plan = DeliveryPlan.objects.create(
            plan_date=target_date,
            truck=truck,
            departure_time=departure_time,
            total_weight=total_weight,
            total_volume=total_volume,
            route_distance_km=0  # 後で計算
        )
        
        # 配送順序の作成
        current_time = departure_time
        for i, order_idx in enumerate(route_indices):
            if order_idx < len(orders):
                order = orders[order_idx]
                travel_time = 30 if i == 0 else 20  # 分
                current_time += timedelta(minutes=travel_time)
                
                PlanOrderDetail.objects.create(
                    plan=plan,
                    shipping_order=order,
                    delivery_sequence=i + 1,
                    estimated_arrival=current_time,
                    travel_time_minutes=travel_time
                )
        
        # 積載商品の記録（パレットとバラ積みを区別）
        for i, (item, position) in enumerate(zip(items, positions)):
            if item.item_code == 'PALLET':
                # パレットの場合は代表商品を使用
                try:
                    representative_item = Item.objects.first()
                    if representative_item:
                        PlanItemLoad.objects.create(
                            plan=plan,
                            shipping_order=orders[i % len(orders)],
                            item=representative_item,
                            quantity=1,
                            position_x=position.x,
                            position_y=position.y,
                            rotation=position.rotation
                        )
                except Exception:
                    pass
            else:
                # バラ積み商品の場合
                try:
                    item_obj = Item.objects.get(item_code=item.item_code)
                    PlanItemLoad.objects.create(
                        plan=plan,
                        shipping_order=orders[i % len(orders)],
                        item=item_obj,
                        quantity=item.quantity,
                        position_x=position.x,
                        position_y=position.y,
                        rotation=position.rotation
                    )
                except Item.DoesNotExist:
                    pass
        
        return plan
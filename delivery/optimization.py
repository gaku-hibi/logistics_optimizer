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
    PlanOrderDetail, PlanItemLoad, Item, PalletConfiguration,
    UnifiedPallet, LoadPallet, PalletLoadHistory,
    PalletizePlan, PalletDetail, PalletItem, LooseItem
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
    shipping_order_id: int = None  # 出荷依頼ID


@dataclass
class Pallet:
    """パレットを表すクラス"""
    width: int = 100  # パレット幅
    depth: int = 100  # パレット奥行
    height: int = 80   # 積み上げ高さ
    max_weight: float = 100  # 最大重量
    boxes: List[Box] = None
    current_height: int = 0  # 現在の積み上げ高さ
    
    def __post_init__(self):
        if self.boxes is None:
            self.boxes = []
    
    @classmethod
    def from_config(cls, config: 'PalletConfiguration'):
        """設定からパレットを作成"""
        return cls(
            width=config.width,
            depth=config.depth,
            height=config.max_height,
            max_weight=config.max_weight
        )
    
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
    
    def __init__(self, pallet_config=None):
        """
        Args:
            pallet_config: PalletConfiguration インスタンス。Noneの場合はデフォルト設定を使用
        """
        if pallet_config is None:
            pallet_config = PalletConfiguration.get_default()
        
        self.pallet_width = pallet_config.width     # cm
        self.pallet_depth = pallet_config.depth     # cm
        self.max_height = pallet_config.max_height  # cm
        self.max_weight = pallet_config.max_weight  # kg
        self.config = pallet_config
    
    def can_palletize(self, box: Box) -> bool:
        """商品がパレタイズ可能かチェック"""
        # 回転も考慮して、どちらかの向きで収まるかチェック
        fits_normal = (box.width <= self.pallet_width and box.depth <= self.pallet_depth)
        fits_rotated = (box.depth <= self.pallet_width and box.width <= self.pallet_depth)
        return (fits_normal or fits_rotated) and box.height <= self.max_height
    
    def pack_pallet(self, boxes: List[Box]) -> Tuple[List[Pallet], List[Box]]:
        """箱をパレットに詰める（3D First Fit Decreasing + 出荷依頼別分離）"""
        pallets = []
        remaining_boxes = []
        
        # 出荷依頼別にグループ化
        order_groups = {}
        for box in boxes:
            order_id = box.shipping_order_id
            if order_id not in order_groups:
                order_groups[order_id] = []
            order_groups[order_id].append(box)
        
        print(f"出荷依頼別グループ数: {len(order_groups)}")
        
        # 各出荷依頼グループを個別にパレタイズ
        for order_id, order_boxes in order_groups.items():
            print(f"出荷依頼ID {order_id}: {len(order_boxes)}個の商品をパレタイズ")
            
            # 体積順でソート（大きい順）- より効率的なパッキングのため
            sorted_boxes = sorted(order_boxes, key=lambda b: b.width * b.depth * b.height, reverse=True)
            
            for box in sorted_boxes:
                if not self.can_palletize(box):
                    remaining_boxes.append(box)
                    continue
                
                placed = False
                
                # 既存パレットに配置可能かチェック（同じ出荷依頼のパレットのみ）
                for pallet in pallets:
                    # パレットが同じ出荷依頼の商品のみを含むかチェック
                    if pallet.boxes and pallet.boxes[0].shipping_order_id == order_id:
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
                    new_pallet = Pallet.from_config(self.config)
                    box.x, box.y, box.z = 0, 0, 0
                    new_pallet.boxes.append(box)
                    new_pallet.current_height = box.height
                    pallets.append(new_pallet)
                    print(f"出荷依頼ID {order_id} 用の新しいパレット #{len(pallets)} を作成")
        
        print(f"総パレット数: {len(pallets)}")
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
            # トラックのサイズを超えないかチェック
            if width > self.truck_width or depth > self.truck_depth:
                continue
                
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
    
    def optimize_with_unified_pallets(self, orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """統一パレットシステムを使用した配送最適化"""
        plans = []
        
        print(f"=== 統一パレット最適化開始 ===")
        print(f"注文数: {len(orders)}")
        
        try:
            with transaction.atomic():
                # 1. 利用可能なUnifiedPalletを取得
                print("1. UnifiedPallet取得開始")
                available_pallets = self._get_available_unified_pallets(orders, target_date)
                print(f"取得されたパレット数: {len(available_pallets)}")
                
                if not available_pallets:
                    print("利用可能なパレットがありません。処理を終了します。")
                    return plans
                
                # 2. 注文を地域別にグループ化
                grouped_orders = self._group_orders_by_region(orders)
                
                # 3. 各地域に対してパレットを割り当て
                print(f"地域数: {len(grouped_orders)}")
                for region, region_orders in grouped_orders.items():
                    print(f"=== 地域 {region} の処理開始 (注文数: {len(region_orders)}) ===")
                    
                    region_pallets = self._allocate_pallets_for_region(
                        region_orders, available_pallets
                    )
                    
                    if not region_pallets:
                        print(f"警告: 地域 {region} に割り当てるパレットがありません")
                        continue
                    
                    # 使用したパレットを削除
                    for pallet in region_pallets:
                        if pallet in available_pallets:
                            available_pallets.remove(pallet)
                    
                    # 4. トラックに積載
                    truck_plans = self._pack_trucks_with_unified_pallets(
                        region_pallets, region_orders, target_date
                    )
                    
                    if truck_plans:
                        print(f"地域 {region} で {len(truck_plans)} の配送計画を作成")
                        plans.extend(truck_plans)
                    else:
                        print(f"警告: 地域 {region} でトラック積載に失敗")
                
        except Exception as e:
            print(f"統一パレット最適化エラー: {e}")
            import traceback
            traceback.print_exc()
            raise Exception(f"統一パレット最適化処理中にエラーが発生しました: {e}")
        
        return plans
    
    def optimize(self, orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """配送最適化を実行"""
        plans = []
        
        try:
            with transaction.atomic():
                # 1. 全体のパレタイズ設計結果を一度だけ取得
                all_pallets, all_loose_items = self._get_or_create_palletize_result(orders, target_date)
                
                # 2. 注文を地域別にグループ化
                grouped_orders = self._group_orders_by_region(orders)
                
                # 3. 各地域に対して必要なパレットとバラ積み商品を割り当て
                remaining_pallets = all_pallets.copy()
                remaining_loose_items = all_loose_items.copy()
                
                for region, region_orders in grouped_orders.items():
                    # 地域の注文に必要なパレットとバラ積み商品を特定
                    region_pallets, region_loose_items = self._allocate_items_for_region(
                        region_orders, remaining_pallets, remaining_loose_items
                    )
                    
                    # 使用したパレットとバラ積み商品を削除
                    for pallet in region_pallets:
                        if pallet in remaining_pallets:
                            remaining_pallets.remove(pallet)
                    
                    for item in region_loose_items:
                        if item in remaining_loose_items:
                            remaining_loose_items.remove(item)
                    
                    # 4. トラックに積載
                    truck_plans = self._pack_trucks(region_pallets, region_loose_items, region_orders, target_date)
                    
                    plans.extend(truck_plans)
                
        except Exception as e:
            print(f"最適化エラー: {e}")
            import traceback
            traceback.print_exc()
            
            # エラーの詳細を分析
            error_type = type(e).__name__
            error_msg = str(e)
            
            if "PalletConfiguration" in error_msg:
                raise Exception(f"パレット設定エラー: {error_msg}")
            elif "Truck" in error_msg:
                raise Exception(f"トラック情報エラー: {error_msg}")
            elif "Item" in error_msg:
                raise Exception(f"商品情報エラー: {error_msg}")
            elif "database" in error_msg.lower():
                raise Exception(f"データベースエラー: {error_msg}")
            else:
                raise Exception(f"最適化処理中にエラーが発生しました ({error_type}): {error_msg}")
        
        return plans
    
    def _allocate_items_for_region(self, region_orders: List[ShippingOrder], 
                                  available_pallets: List[Pallet], 
                                  available_loose_items: List[Box]) -> Tuple[List[Pallet], List[Box]]:
        """地域の注文に必要なパレットとバラ積み商品を割り当て"""
        region_pallets = []
        region_loose_items = []
        
        # 地域の注文から必要な商品を特定
        needed_items = {}
        for order in region_orders:
            for order_item in order.order_items.all():
                item_code = order_item.item.item_code
                if item_code not in needed_items:
                    needed_items[item_code] = 0
                needed_items[item_code] += order_item.quantity
        
        print(f"地域の必要商品: {needed_items}")
        
        # パレットから必要な商品を含むものを選択
        for pallet in available_pallets:
            pallet_has_needed_items = False
            for box in pallet.boxes:
                if box.item_code in needed_items and needed_items[box.item_code] > 0:
                    pallet_has_needed_items = True
                    needed_items[box.item_code] -= box.quantity
                    break
            
            if pallet_has_needed_items:
                region_pallets.append(pallet)
        
        # バラ積み商品から必要なものを選択
        for loose_item in available_loose_items:
            if loose_item.item_code in needed_items and needed_items[loose_item.item_code] > 0:
                region_loose_items.append(loose_item)
                needed_items[loose_item.item_code] -= loose_item.quantity
        
        print(f"地域に割り当てたパレット数: {len(region_pallets)}")
        print(f"地域に割り当てたバラ積み商品数: {len(region_loose_items)}")
        
        return region_pallets, region_loose_items
    
    def _group_orders_by_region(self, orders: List[ShippingOrder]) -> Dict[str, List[ShippingOrder]]:
        """注文を地域別にグループ化"""
        groups = {}
        
        print(f"=== 地域グループ化開始 (注文数: {len(orders)}) ===")
        
        for order in orders:
            # 住所から市区町村を抽出（簡易版）
            address = order.destination.address
            region = self._extract_region(address)
            
            if region not in groups:
                groups[region] = []
            groups[region].append(order)
            
            print(f"注文ID {order.id}: {address} -> {region}")
        
        # 地域別集計を表示
        for region, region_orders in groups.items():
            print(f"地域 {region}: {len(region_orders)}件")
        
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
    
    def _get_or_create_palletize_result(self, orders: List[ShippingOrder], target_date) -> Tuple[List[Pallet], List[Box]]:
        """既存のパレタイズ設計結果を取得、なければ新規作成"""
        from .models import PalletizePlan, PalletDetail, PalletItem, LooseItem
        
        # 既存のパレタイズ設計結果を検索（最新のものを取得）
        try:
            palletize_plan = PalletizePlan.objects.filter(delivery_date=target_date).order_by('-created_at').first()
            if not palletize_plan:
                raise PalletizePlan.DoesNotExist()
            
            # 既存結果からパレットとバラ積み商品を復元
            pallets = []
            loose_items = []
            
            # パレットを復元
            for pallet_detail in palletize_plan.pallets.all():
                pallet = Pallet()
                pallet.current_height = 0
                
                # パレット内の商品を復元
                for pallet_item in pallet_detail.items.all():
                    # 出荷依頼IDを特定するために、商品から関連する注文を検索
                    shipping_order_id = None
                    item_code = pallet_item.part.parts_code if pallet_item.part else pallet_item.item.item_code
                    
                    # 提供された注文リストから対応する出荷依頼を検索
                    for order in orders:
                        for order_item in order.order_items.all():
                            if order_item.item.item_code == item_code:
                                shipping_order_id = order.id
                                break
                        if shipping_order_id:
                            break
                    
                    box = Box(
                        width=pallet_item.width,
                        depth=pallet_item.depth,
                        height=pallet_item.height,
                        weight=pallet_item.weight,
                        item_code=item_code,
                        quantity=1,
                        shipping_order_id=shipping_order_id
                    )
                    box.x = pallet_item.position_x
                    box.y = pallet_item.position_y
                    box.z = pallet_item.position_z
                    pallet.boxes.append(box)
                    pallet.current_height = max(pallet.current_height, box.z + box.height)
                
                pallets.append(pallet)
            
            # バラ積み商品を復元
            for loose_item in palletize_plan.loose_items.all():
                # 出荷依頼IDを特定するために、商品から関連する注文を検索
                shipping_order_id = None
                item_code = loose_item.item.item_code
                
                # 提供された注文リストから対応する出荷依頼を検索
                for order in orders:
                    for order_item in order.order_items.all():
                        if order_item.item.item_code == item_code:
                            shipping_order_id = order.id
                            break
                    if shipping_order_id:
                        break
                
                box = Box(
                    width=loose_item.width,
                    depth=loose_item.depth,
                    height=loose_item.height,
                    weight=loose_item.weight,
                    item_code=item_code,
                    quantity=1,
                    shipping_order_id=shipping_order_id
                )
                loose_items.append(box)
            
            return pallets, loose_items
            
        except PalletizePlan.DoesNotExist:
            # 既存の設計結果がない場合は新規作成
            return self._palletize_orders(orders)
    
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
                            quantity=1,  # 各箱は個別に扱う
                            shipping_order_id=order.id  # 出荷依頼IDを設定
                        )
                        all_boxes.append(box)
                else:
                    print(f"警告: 商品 {item.name} ({item.item_code}) に寸法または重量が設定されていません")
        
        return self.pallet_optimizer.pack_pallet(all_boxes)
    
    def _pack_trucks(self, pallets: List[Pallet], loose_items: List[Box], 
                    orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """トラックに積載して配送計画を作成（パレット単位＋バラ積み）"""
        plans = []
        trucks = list(Truck.objects.filter(width__gt=0, depth__gt=0).order_by('-payload'))
        
        if not trucks:
            print("警告: 使用可能なトラックがありません")
            return plans
        
        # パレットとバラ積み商品を分けて管理
        remaining_pallets = pallets.copy()
        remaining_loose_items = loose_items.copy()
        
        # すべての商品が積載されるまで繰り返し
        while remaining_pallets or remaining_loose_items:
            truck_found = False
            
            # 各トラックタイプを試す
            for truck in trucks:
                if not remaining_pallets and not remaining_loose_items:
                    break
                
                # トラックに積載するアイテムを選択
                truck_pallets = []
                truck_loose_items = []
                current_weight = 0
                truck_capacity = truck.payload
                
                # 2D配置でパッキング可能な商品を選択
                packer = BinPacking2D(truck.width, truck.depth)
                test_items = []
                test_pallets = []
                test_loose = []
                
                # 1. パレットを優先的に積載（サイズと重量をチェック）
                for pallet in remaining_pallets:
                    pallet_weight = pallet.get_total_weight()
                    # パレットがトラックに入るかサイズをチェック
                    if (pallet.width <= truck.width and pallet.depth <= truck.depth and 
                        current_weight + pallet_weight <= truck_capacity):
                        pallet_box = Box(
                            width=pallet.width,
                            depth=pallet.depth,
                            height=pallet.current_height,
                            weight=pallet_weight,
                            item_code='PALLET',
                            quantity=1
                        )
                        test_items.append(pallet_box)
                        test_pallets.append(pallet)
                        current_weight += pallet_weight
                
                # 2. 残り重量でバラ積み商品を積載
                for loose_item in remaining_loose_items:
                    if current_weight + loose_item.weight <= truck_capacity:
                        test_items.append(loose_item)
                        test_loose.append(loose_item)
                        current_weight += loose_item.weight
                
                # 3. 積載するアイテムがある場合、配送計画を作成
                if test_items:
                    # 2D配置を試行
                    positions = packer.pack(test_items)
                    
                    if positions:
                        # 実際に積載されたアイテムを特定
                        loaded_pallets = []
                        loaded_loose = []
                        
                        for i, pos in enumerate(positions):
                            if pos:
                                if i < len(test_pallets):
                                    loaded_pallets.append(test_pallets[i])
                                else:
                                    loose_idx = i - len(test_pallets)
                                    if loose_idx < len(test_loose):
                                        loaded_loose.append(test_loose[loose_idx])
                        
                        if loaded_pallets or loaded_loose:
                            # 配送計画を作成
                            all_loaded_items = []
                            for pallet in loaded_pallets:
                                pallet_box = Box(
                                    width=pallet.width,
                                    depth=pallet.depth,
                                    height=pallet.current_height,
                                    weight=pallet.get_total_weight(),
                                    item_code='PALLET',
                                    quantity=1
                                )
                                all_loaded_items.append(pallet_box)
                            all_loaded_items.extend(loaded_loose)
                            
                            plan = self._create_delivery_plan(
                                truck, orders, target_date, all_loaded_items, positions[:len(all_loaded_items)],
                                loaded_pallets, loaded_loose
                            )
                            plans.append(plan)
                            
                            # 積載されたアイテムを残りから削除
                            for pallet in loaded_pallets:
                                remaining_pallets.remove(pallet)
                            for item in loaded_loose:
                                remaining_loose_items.remove(item)
                            
                            truck_found = True
                            break
            
            # どのトラックにも積載できなかった場合
            if not truck_found:
                if remaining_pallets or remaining_loose_items:
                    print(f"警告: パレット{len(remaining_pallets)}個、バラ積み{len(remaining_loose_items)}個がどのトラックにも積載できませんでした")
                    # 最大のトラックを強制的に使用
                    truck = trucks[0]  # 最大積載量のトラック
                    
                    # パレットを優先して1つずつ積載
                    if remaining_pallets:
                        forced_pallet = remaining_pallets[0]
                        pallet_box = Box(
                            width=forced_pallet.width,
                            depth=forced_pallet.depth,
                            height=forced_pallet.current_height,
                            weight=forced_pallet.get_total_weight(),
                            item_code='PALLET',
                            quantity=1
                        )
                        plan = self._create_delivery_plan(
                            truck, orders, target_date, [pallet_box], [Position(
                                x=0, y=0, width=pallet_box.width, depth=pallet_box.depth, rotation=0
                            )],
                            [forced_pallet], []
                        )
                        plans.append(plan)
                        remaining_pallets.remove(forced_pallet)
                    elif remaining_loose_items:
                        forced_item = remaining_loose_items[0]
                        plan = self._create_delivery_plan(
                            truck, orders, target_date, [forced_item], [Position(
                                x=0, y=0, width=forced_item.width, depth=forced_item.depth, rotation=0
                            )],
                            [], [forced_item]
                        )
                        plans.append(plan)
                        remaining_loose_items.remove(forced_item)
        
        return plans
    
    def _create_delivery_plan(self, truck: Truck, orders: List[ShippingOrder], 
                             target_date, items: List[Box], positions: List[Position],
                             truck_pallets: List[Pallet] = None, truck_loose_items: List[Box] = None) -> DeliveryPlan:
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
        pallet_index = 0
        for i, (item, position) in enumerate(zip(items, positions)):
            if item.item_code == 'PALLET':
                # パレットの場合：パレット内の全商品を記録
                if truck_pallets and pallet_index < len(truck_pallets):
                    pallet = truck_pallets[pallet_index]
                    for box in pallet.boxes:
                        try:
                            item_obj = Item.objects.get(item_code=box.item_code)
                            # パレット内の商品を適切な出荷依頼に関連付け
                            related_order = self._find_related_order(orders, item_obj)
                            if related_order:
                                PlanItemLoad.objects.create(
                                    plan=plan,
                                    shipping_order=related_order,
                                    item=item_obj,
                                    quantity=1,
                                    position_x=position.x + box.x,  # パレット内の相対位置を加算
                                    position_y=position.y + box.y,
                                    rotation=position.rotation
                                )
                        except Item.DoesNotExist:
                            pass
                    pallet_index += 1
            else:
                # バラ積み商品の場合
                try:
                    item_obj = Item.objects.get(item_code=item.item_code)
                    related_order = self._find_related_order(orders, item_obj)
                    if related_order:
                        PlanItemLoad.objects.create(
                            plan=plan,
                            shipping_order=related_order,
                            item=item_obj,
                            quantity=item.quantity,
                            position_x=position.x,
                            position_y=position.y,
                            rotation=position.rotation
                        )
                except Item.DoesNotExist:
                    pass
        
        return plan
    
    def _find_related_order(self, orders: List[ShippingOrder], item: Item) -> ShippingOrder:
        """商品に関連する出荷依頼を見つける"""
        for order in orders:
            for order_item in order.order_items.all():
                if order_item.item == item:
                    return order
                # セット品の場合は部品も確認
                if order_item.item.parts.filter(parts_code=item.item_code).exists():
                    return order
        return orders[0] if orders else None
    
    def _get_available_unified_pallets(self, orders: List[ShippingOrder], target_date) -> List['UnifiedPallet']:
        """利用可能なUnifiedPalletを取得"""
        # 指定日の注文に関連するUnifiedPalletを取得
        order_ids = [order.id for order in orders]
        print(f"=== UnifiedPallet取得 ===")
        print(f"対象注文ID: {order_ids}")
        
        # すでに使用されているパレットを除外
        used_pallet_ids = PalletLoadHistory.objects.filter(
            status__in=['USED', 'ALLOCATED']
        ).values_list('pallet_id', flat=True)
        print(f"使用済みパレットID: {list(used_pallet_ids)}")
        
        available_pallets = UnifiedPallet.objects.filter(
            delivery_date=target_date,
            shipping_order_id__in=order_ids
        ).exclude(
            id__in=used_pallet_ids
        ).order_by('pallet_type', '-weight')
        
        print(f"利用可能パレット数: {available_pallets.count()}")
        
        # 既存のUnifiedPalletがある場合も詳細を表示
        if available_pallets.exists():
            print(f"既存のUnifiedPallet詳細:")
            for pallet in available_pallets:
                print(f"  ID={pallet.id}, type={pallet.pallet_type}, order_id={pallet.shipping_order_id}")
            return list(available_pallets)
        
        # UnifiedPalletが存在しない場合、パレタイズ設計から作成を試みる
        print("UnifiedPalletが存在しません。パレタイズ設計から作成を試みます。")
        print(f"検索対象日: {target_date}")
        
        try:
            # パレタイズ設計を検索
            palletize_plans = PalletizePlan.objects.filter(delivery_date=target_date)
            print(f"パレタイズ設計検索結果: {palletize_plans.count()}件")
            
            palletize_plan = palletize_plans.first()
            if palletize_plan:
                print(f"パレタイズ設計発見: ID={palletize_plan.id}")
                print(f"  パレット数: {palletize_plan.pallets.count()}")
                print(f"  バラ積み商品数: {palletize_plan.loose_items.count()}")
                
                created_pallets = self._create_unified_pallets_from_palletize_plan(palletize_plan, orders)
                print(f"作成されたUnifiedPallet数: {len(created_pallets)}")
                return created_pallets
            else:
                print("パレタイズ設計が見つかりません")
                # デバッグ: 全てのパレタイズ設計を確認
                all_plans = PalletizePlan.objects.all()
                print(f"全パレタイズ設計数: {all_plans.count()}")
                if all_plans.exists():
                    print("既存のパレタイズ設計:")
                    for plan in all_plans:
                        print(f"  ID={plan.id}, 日付={plan.delivery_date}")
        except Exception as e:
            print(f"UnifiedPallet作成エラー: {e}")
            import traceback
            traceback.print_exc()
        
        return []
    
    def _create_unified_pallets_from_palletize_plan(self, palletize_plan: 'PalletizePlan', orders: List[ShippingOrder]) -> List['UnifiedPallet']:
        """パレタイズ設計からUnifiedPalletを作成"""
        created_pallets = []
        
        try:
            # パレット設定を取得
            pallet_config = PalletConfiguration.get_default()
            
            # REALパレットの作成
            for pallet_detail in palletize_plan.pallets.all():
                # パレット詳細の最初の商品の注文を代表として設定
                first_item = pallet_detail.items.first()
                representative_order = first_item.shipping_order if first_item else orders[0]
                
                # パレット詳細からUnifiedPalletを作成
                unified_pallet = UnifiedPallet.objects.create(
                    pallet_type='REAL',
                    pallet_detail=pallet_detail,
                    delivery_date=palletize_plan.delivery_date,
                    width=pallet_config.width,
                    depth=pallet_config.depth,
                    height=pallet_config.max_height,
                    weight=pallet_detail.total_weight,
                    volume=pallet_detail.total_volume,
                    shipping_order=representative_order  # 代表的な注文を設定
                )
                
                # パレットに含まれる全ての注文を関連付ける
                pallet_orders = []
                for pallet_item in pallet_detail.items.all():
                    if pallet_item.shipping_order not in pallet_orders:
                        pallet_orders.append(pallet_item.shipping_order)
                unified_pallet.related_orders.set(pallet_orders)
                
                created_pallets.append(unified_pallet)
                
                # デバッグ情報を追加
                pallet_order_ids = list(pallet_detail.items.values_list('shipping_order_id', flat=True).distinct())
                print(f"REALパレット作成: ID={unified_pallet.id}, 重量={unified_pallet.weight}, 含まれる注文ID: {pallet_order_ids}")
            
            # VIRTUALパレット（バラ積み）の作成
            for loose_item in palletize_plan.loose_items.all():
                # バラ積み商品の場合、数量は1として扱う
                # 体積を計算
                volume = loose_item.width * loose_item.depth * loose_item.height
                
                unified_pallet = UnifiedPallet.objects.create(
                    pallet_type='VIRTUAL',
                    item=loose_item.item,
                    item_quantity=1,  # バラ積み商品の数量は1
                    delivery_date=palletize_plan.delivery_date,
                    width=loose_item.width,
                    depth=loose_item.depth,
                    height=loose_item.height,
                    weight=loose_item.weight,
                    volume=volume,
                    shipping_order=loose_item.shipping_order
                )
                # VIRTUALパレットも関連注文を設定
                unified_pallet.related_orders.set([loose_item.shipping_order])
                
                created_pallets.append(unified_pallet)
                print(f"VIRTUALパレット作成: ID={unified_pallet.id}, 商品={loose_item.item.name}")
                
        except Exception as e:
            print(f"UnifiedPallet作成中にエラー: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        return created_pallets
    
    def _allocate_pallets_for_region(self, region_orders: List[ShippingOrder], 
                                   available_pallets: List['UnifiedPallet']) -> List['UnifiedPallet']:
        """地域の注文に必要なパレットを割り当て"""
        region_pallets = []
        
        # 地域の注文IDセット
        region_order_ids = {order.id for order in region_orders}
        print(f"地域注文ID: {region_order_ids}")
        
        print(f"利用可能パレット数: {len(available_pallets)}")
        
        if not available_pallets:
            print("利用可能なパレットがありません")
            return region_pallets
        
        # 該当する注文のパレットを選択
        for pallet in available_pallets:
            print(f"パレット ID={pallet.id}, type={pallet.pallet_type}, order_id={pallet.shipping_order_id}")
            
            # related_ordersフィールドを使用して判定
            pallet_order_ids = set(pallet.related_orders.values_list('id', flat=True))
            
            print(f"パレット {pallet.id} (type={pallet.pallet_type}) の関連注文ID: {pallet_order_ids}")
            
            # 地域の注文と重複があるかチェック
            if pallet_order_ids & region_order_ids:
                region_pallets.append(pallet)
                print(f"パレット {pallet.id} を地域に割り当て (注文ID: {pallet_order_ids})")
            else:
                print(f"パレット {pallet.id} は地域の注文と一致しません")
        
        print(f"地域に割り当てたパレット数: {len(region_pallets)}")
        return region_pallets
    
    def _group_pallets_by_order(self, pallets: List['UnifiedPallet']) -> dict:
        """パレットを出荷依頼単位でグループ化"""
        order_groups = {}
        
        for pallet in pallets:
            # パレットに関連する全ての注文IDを取得
            related_order_ids = set(pallet.related_orders.values_list('id', flat=True))
            
            if related_order_ids:
                # 複数の注文に関連するパレットは、最初の注文のグループに入れる
                primary_order_id = min(related_order_ids)
                
                if primary_order_id not in order_groups:
                    order_groups[primary_order_id] = []
                order_groups[primary_order_id].append(pallet)
                
                print(f"パレット {pallet.id} を注文 {primary_order_id} のグループに追加")
            else:
                # 関連する注文がない場合は、shipping_orderを使用
                if pallet.shipping_order:
                    order_id = pallet.shipping_order.id
                    if order_id not in order_groups:
                        order_groups[order_id] = []
                    order_groups[order_id].append(pallet)
                    print(f"パレット {pallet.id} を注文 {order_id} のグループに追加（shipping_order使用）")
                else:
                    print(f"警告: パレット {pallet.id} に関連する注文がありません")
        
        print(f"\n出荷依頼グループ数: {len(order_groups)}")
        for order_id, group_pallets in order_groups.items():
            print(f"  注文 {order_id}: {len(group_pallets)}個のパレット")
        
        return order_groups
    
    def _pack_trucks_with_unified_pallets(self, pallets: List['UnifiedPallet'], 
                                        orders: List[ShippingOrder], target_date) -> List[DeliveryPlan]:
        """統一パレットシステムでトラックに積載"""
        plans = []
        trucks = list(Truck.objects.filter(width__gt=0, depth__gt=0).order_by('-payload'))
        
        print(f"=== トラック積載開始 ===")
        print(f"積載対象パレット数: {len(pallets)}")
        print(f"利用可能トラック数: {len(trucks)}")
        
        if not trucks:
            print("警告: 使用可能なトラックがありません")
            return plans
        
        if not pallets:
            print("警告: 積載するパレットがありません")
            return plans
        
        # トラック情報を表示
        for i, truck in enumerate(trucks):
            print(f"トラック{i+1}: {truck.width}x{truck.depth}cm, 積載量{truck.payload}kg")
        
        # 出荷依頼単位でパレットをグループ化
        order_pallet_groups = self._group_pallets_by_order(pallets)
        remaining_order_groups = list(order_pallet_groups.items())
        
        # すべての出荷依頼グループが積載されるまで繰り返し
        while remaining_order_groups:
            truck_found = False
            
            # 各トラックタイプを試す
            for truck in trucks:
                truck_order_groups = []  # このトラックに積載する出荷依頼グループ
                current_weight = 0
                truck_capacity = truck.payload
                
                # 2D配置でパッキング可能な出荷依頼グループを選択
                packer = BinPacking2D(truck.width, truck.depth)
                test_boxes = []
                test_pallets = []
                test_group_info = []  # (order_id, group_pallets) のリスト
                
                for order_id, group_pallets in remaining_order_groups:
                    # 出荷依頼全体の重量・サイズをチェック
                    group_weight = sum(p.weight for p in group_pallets)
                    
                    # 重量制限チェック
                    if current_weight + group_weight > truck_capacity:
                        print(f"注文 {order_id} は重量制限により積載不可 (必要: {group_weight}kg, 残り容量: {truck_capacity - current_weight}kg)")
                        continue
                    
                    # 全パレットがトラックサイズに収まるかチェック
                    group_boxes = []
                    can_fit_all = True
                    
                    for pallet in group_pallets:
                        if pallet.width <= truck.width and pallet.depth <= truck.depth:
                            box = Box(
                                width=pallet.width,
                                depth=pallet.depth,
                                height=pallet.height,
                                weight=pallet.weight,
                                item_code=f'PALLET_{pallet.id}',
                                quantity=1
                            )
                            group_boxes.append(box)
                        else:
                            can_fit_all = False
                            print(f"注文 {order_id} のパレット {pallet.id} はサイズ制限により積載不可")
                            break
                    
                    if can_fit_all:
                        # 現在選択中の他のパレットと一緒に2D配置をテスト
                        temp_boxes = test_boxes + group_boxes
                        temp_packer = BinPacking2D(truck.width, truck.depth)
                        temp_positions = temp_packer.pack(temp_boxes)
                        
                        # 全てのパレットが配置できる場合のみ追加
                        if temp_positions and len([p for p in temp_positions if p]) == len(temp_boxes):
                            test_boxes.extend(group_boxes)
                            test_pallets.extend(group_pallets)
                            test_group_info.append((order_id, group_pallets))
                            current_weight += group_weight
                            print(f"注文 {order_id} ({len(group_pallets)}個のパレット, {group_weight}kg) を積載候補に追加")
                        else:
                            print(f"注文 {order_id} は2D配置制限により積載不可")
                    
                    # トラック容量の80%を超えたら次のトラックを検討
                    if current_weight > truck_capacity * 0.8:
                        break
                
                if test_group_info:
                    # 最終的な2D配置を実行
                    final_positions = packer.pack(test_boxes)
                    
                    if final_positions:
                        # 積載された出荷依頼グループに対応する注文を特定
                        loaded_orders = []
                        for order_id, group_pallets in test_group_info:
                            order = next((o for o in orders if o.id == order_id), None)
                            if order:
                                loaded_orders.append(order)
                        
                        # 配送計画を作成
                        plan = self._create_delivery_plan_with_unified_pallets(
                            truck, loaded_orders, target_date, test_pallets, final_positions[:len(test_pallets)]
                        )
                        plans.append(plan)
                        
                        # 積載された出荷依頼グループを残りから削除
                        for order_id, group_pallets in test_group_info:
                            remaining_order_groups = [(oid, gp) for oid, gp in remaining_order_groups if oid != order_id]
                        
                        print(f"トラック {truck.id} に {len(test_group_info)}個の出荷依頼を積載しました")
                        truck_found = True
                        break
            
            # どのトラックにも積載できなかった場合
            if not truck_found:
                if remaining_order_groups:
                    print(f"警告: {len(remaining_order_groups)}個の出荷依頼がどのトラックにも積載できませんでした")
                    # 最大のトラックを強制的に使用して、1つの出荷依頼を積載
                    truck = trucks[0]  # 最大積載量のトラック
                    forced_order_id, forced_pallets = remaining_order_groups[0]
                    forced_order = next((o for o in orders if o.id == forced_order_id), None)
                    
                    # 強制的に配送計画を作成
                    if forced_order:
                        positions = []
                        for pallet in forced_pallets:
                            positions.append(Position(
                                x=0, 
                                y=0, 
                                width=pallet.width, 
                                depth=pallet.depth, 
                                rotation=0
                            ))
                        plan = self._create_delivery_plan_with_unified_pallets(
                            truck, [forced_order], target_date, forced_pallets, positions
                        )
                        plans.append(plan)
                    
                    # 処理した出荷依頼を削除
                    remaining_order_groups = remaining_order_groups[1:]
                    print(f"強制的に注文 {forced_order_id} を積載しました")
        
        return plans
    
    def _create_delivery_plan_with_unified_pallets(self, truck: Truck, orders: List[ShippingOrder], 
                                                 target_date, pallets: List['UnifiedPallet'], 
                                                 positions: List[Position]) -> DeliveryPlan:
        """統一パレットシステムで配送計画を作成"""
        
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
        total_weight = sum(pallet.weight for pallet in pallets)
        total_volume = sum(pallet.volume for pallet in pallets)
        
        # 出発時刻計算
        departure_time = datetime.combine(target_date, datetime.min.time().replace(hour=8))
        
        # 配送計画作成
        plan = DeliveryPlan.objects.create(
            plan_date=target_date,
            truck=truck,
            departure_time=departure_time,
            total_weight=total_weight,
            total_volume=total_volume,
            route_distance_km=0
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
        
        # LoadPalletとPalletLoadHistoryの作成
        for i, (pallet, position) in enumerate(zip(pallets, positions)):
            # LoadPalletを作成
            LoadPallet.objects.create(
                plan=plan,
                pallet=pallet,
                position_x=position.x,
                position_y=position.y,
                rotation=position.rotation,
                load_sequence=i + 1
            )
            
            # PalletLoadHistoryを作成
            PalletLoadHistory.objects.create(
                pallet=pallet,
                plan=plan,
                status='USED'
            )
        
        return plan
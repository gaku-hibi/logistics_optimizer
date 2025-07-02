import numpy as np
from typing import List, Tuple, Dict
from datetime import datetime, timedelta
from geopy.distance import geodesic
from geopy.geocoders import Nominatim
import time


class BinPacking2D:
    """2Dビンパッキングアルゴリズム（First Fit Decreasing）"""
    
    def __init__(self, bin_width: float, bin_depth: float):
        self.bin_width = bin_width
        self.bin_depth = bin_depth
        self.packed_items = []
        self.free_rectangles = [(0, 0, bin_width, bin_depth)]
    
    def can_fit(self, width: float, depth: float) -> Tuple[bool, Tuple[float, float]]:
        """アイテムが配置可能かチェック"""
        for x, y, w, h in self.free_rectangles:
            if width <= w and depth <= h:
                return True, (x, y)
            if depth <= w and width <= h:  # 90度回転
                return True, (x, y)
        return False, (0, 0)
    
    def place_item(self, item_id: int, width: float, depth: float) -> Tuple[bool, Tuple[float, float]]:
        """アイテムを配置"""
        best_fit = None
        best_area = float('inf')
        
        for i, (x, y, w, h) in enumerate(self.free_rectangles):
            if width <= w and depth <= h:
                area = w * h
                if area < best_area:
                    best_area = area
                    best_fit = (i, x, y, width, depth, False)
            
            if depth <= w and width <= h:  # 90度回転
                area = w * h
                if area < best_area:
                    best_area = area
                    best_fit = (i, x, y, depth, width, True)
        
        if best_fit is None:
            return False, (0, 0)
        
        rect_idx, x, y, placed_w, placed_h, rotated = best_fit
        
        # アイテムを配置
        self.packed_items.append({
            'id': item_id,
            'x': x,
            'y': y,
            'width': placed_w,
            'depth': placed_h,
            'rotated': rotated
        })
        
        # 空き領域を更新
        old_rect = self.free_rectangles.pop(rect_idx)
        old_x, old_y, old_w, old_h = old_rect
        
        # 新しい空き領域を生成
        if old_w > placed_w:
            self.free_rectangles.append((x + placed_w, old_y, old_w - placed_w, old_h))
        if old_h > placed_h:
            self.free_rectangles.append((old_x, y + placed_h, old_w, old_h - placed_h))
        
        return True, (x, y)
    
    def get_utilization(self) -> float:
        """荷台使用率を計算"""
        used_area = sum(item['width'] * item['depth'] for item in self.packed_items)
        total_area = self.bin_width * self.bin_depth
        return (used_area / total_area) * 100


class RouteOptimizer:
    """配送ルート最適化（Nearest Neighbor法）"""
    
    def __init__(self):
        self.geolocator = Nominatim(user_agent="logistics_optimizer")
        self.location_cache = {}
    
    def get_coordinates(self, address: str) -> Tuple[float, float]:
        """住所から座標を取得"""
        if address in self.location_cache:
            return self.location_cache[address]
        
        try:
            time.sleep(1)  # APIレート制限対策
            location = self.geolocator.geocode(address, country_codes=['jp'])
            if location:
                coords = (location.latitude, location.longitude)
                self.location_cache[address] = coords
                return coords
        except Exception as e:
            print(f"Geocoding error for {address}: {e}")
        
        # デフォルト座標（東京駅）
        return (35.6812, 139.7671)
    
    def calculate_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """2点間の距離を計算（km）"""
        return geodesic(coord1, coord2).kilometers
    
    def optimize_route(self, depot: str, destinations: List[str]) -> Tuple[List[str], float]:
        """最適な配送ルートを計算"""
        if not destinations:
            return [], 0
        
        # 座標を取得
        depot_coord = self.get_coordinates(depot)
        dest_coords = {dest: self.get_coordinates(dest) for dest in destinations}
        
        # Nearest Neighbor法でルートを最適化
        route = []
        total_distance = 0
        current_coord = depot_coord
        remaining = set(destinations)
        
        while remaining:
            nearest = None
            min_distance = float('inf')
            
            for dest in remaining:
                distance = self.calculate_distance(current_coord, dest_coords[dest])
                if distance < min_distance:
                    min_distance = distance
                    nearest = dest
            
            if nearest:
                route.append(nearest)
                total_distance += min_distance
                current_coord = dest_coords[nearest]
                remaining.remove(nearest)
        
        # 最後に倉庫に戻る
        total_distance += self.calculate_distance(current_coord, depot_coord)
        
        return route, total_distance
    
    def estimate_delivery_time(self, distance: float) -> float:
        """配送時間を推定（分）"""
        # 平均速度30km/h + 各配送先での作業時間10分
        average_speed = 30  # km/h
        delivery_time_per_stop = 10  # minutes
        travel_time = (distance / average_speed) * 60
        return travel_time + delivery_time_per_stop


class DeliveryOptimizer:
    """統合配送最適化システム"""
    
    def __init__(self):
        self.route_optimizer = RouteOptimizer()
    
    def optimize_delivery(self, products: List[Dict], trucks: List[Dict], 
                         dispatch_time: datetime, depot_address: str = "東京都千代田区丸の内1-9-1") -> Dict:
        """配送計画を最適化"""
        
        # 商品を体積でソート（大きい順）
        sorted_products = sorted(products, key=lambda p: p['width'] * p['depth'], reverse=True)
        
        # 配送期限でグループ化
        deadline_groups = {}
        for product in sorted_products:
            deadline_date = product['delivery_deadline'].date()
            if deadline_date not in deadline_groups:
                deadline_groups[deadline_date] = []
            deadline_groups[deadline_date].append(product)
        
        results = {
            'truck_assignments': [],
            'unassigned_products': [],
            'total_trucks_needed': 0
        }
        
        # 各期限日ごとに処理
        for deadline_date, products_group in sorted(deadline_groups.items()):
            available_trucks = trucks.copy()
            
            for product in products_group:
                assigned = False
                
                # 利用可能なトラックを試す
                for truck in available_trucks:
                    # 重量チェック
                    current_weight = sum(ta.get('total_weight', 0) for ta in results['truck_assignments'] 
                                       if ta.get('truck_id') == truck['id'])
                    if current_weight + product['weight'] > truck['max_weight']:
                        continue
                    
                    # 既存の割り当てを確認
                    truck_assignment = next((ta for ta in results['truck_assignments'] 
                                           if ta['truck_id'] == truck['id'] and ta['date'] == deadline_date), None)
                    
                    if not truck_assignment:
                        # 新しいトラック割り当て
                        packer = BinPacking2D(truck['bed_width'], truck['bed_depth'])
                        success, position = packer.place_item(product['id'], product['width'], product['depth'])
                        
                        if success:
                            truck_assignment = {
                                'truck_id': truck['id'],
                                'truck_name': truck['name'],
                                'date': deadline_date,
                                'packer': packer,
                                'products': [product],
                                'destinations': [product['destination_address']],
                                'total_weight': product['weight']
                            }
                            results['truck_assignments'].append(truck_assignment)
                            assigned = True
                            break
                    else:
                        # 既存のトラックに追加
                        success, position = truck_assignment['packer'].place_item(
                            product['id'], product['width'], product['depth'])
                        
                        if success:
                            truck_assignment['products'].append(product)
                            if product['destination_address'] not in truck_assignment['destinations']:
                                truck_assignment['destinations'].append(product['destination_address'])
                            truck_assignment['total_weight'] += product['weight']
                            assigned = True
                            break
                
                if not assigned:
                    results['unassigned_products'].append(product)
        
        # ルート最適化と時間推定
        for assignment in results['truck_assignments']:
            route, distance = self.route_optimizer.optimize_route(depot_address, assignment['destinations'])
            assignment['route'] = route
            assignment['total_distance'] = distance
            assignment['estimated_time'] = self.route_optimizer.estimate_delivery_time(distance)
            assignment['utilization'] = assignment['packer'].get_utilization()
            
            # 到着予定時刻を計算
            arrival_time = dispatch_time + timedelta(minutes=assignment['estimated_time'])
            assignment['estimated_arrival'] = arrival_time
        
        results['total_trucks_needed'] = len(results['truck_assignments'])
        
        return results
"""
サンプルデータ投入コマンド
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from datetime import datetime, date, timedelta
import random

from delivery.models import (
    Item, Shipper, Destination, Truck, ShippingOrder, OrderItem
)


class Command(BaseCommand):
    help = 'サンプルデータを投入します'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='既存データをクリアしてから新規作成',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('既存データをクリアしています...')
            self._clear_existing_data()
        
        self.stdout.write('サンプルデータを作成中...')
        
        with transaction.atomic():
            # 商品データ
            self._create_items()
            
            # 荷主データ
            self._create_shippers()
            
            # 配送先データ
            self._create_destinations()
            
            # トラックデータ
            self._create_trucks()
            
            # 出荷依頼データ
            self._create_shipping_orders()
        
        self.stdout.write(
            self.style.SUCCESS('サンプルデータの作成が完了しました。')
        )
        
        # 作成されたデータの統計を表示
        self._show_statistics()

    def _clear_existing_data(self):
        """既存データをクリア"""
        from delivery.models import DeliveryPlan, PlanOrderDetail, PlanItemLoad
        
        # 配送計画関連のデータを削除
        PlanItemLoad.objects.all().delete()
        PlanOrderDetail.objects.all().delete()
        DeliveryPlan.objects.all().delete()
        
        # 出荷依頼関連のデータを削除
        OrderItem.objects.all().delete()
        ShippingOrder.objects.all().delete()
        
        # マスタデータを削除
        Truck.objects.all().delete()
        Destination.objects.all().delete()
        Shipper.objects.all().delete()
        Item.objects.all().delete()
        
        self.stdout.write('既存データのクリアが完了しました。')

    def _show_statistics(self):
        """作成されたデータの統計を表示"""
        self.stdout.write('\n=== 作成データ統計 ===')
        self.stdout.write(f'商品: {Item.objects.count()} 件')
        self.stdout.write(f'荷主: {Shipper.objects.count()} 件')
        self.stdout.write(f'配送先: {Destination.objects.count()} 件')
        self.stdout.write(f'トラック: {Truck.objects.count()} 件')
        self.stdout.write(f'出荷依頼: {ShippingOrder.objects.count()} 件')
        self.stdout.write(f'注文商品: {OrderItem.objects.count()} 件')
        
        # 商品カテゴリ別統計
        self.stdout.write('\n=== 商品カテゴリ別統計 ===')
        categories = {
            'PC': 'PC・電子機器',
            'SP': 'スマートフォン関連',
            'BK': '書籍・文具',
            'HE': '家電製品',
            'LI': '生活用品',
            'CL': '衣類・アパレル',
            'FD': '食品・飲料',
            'PK': '梱包材',
        }
        
        for prefix, category_name in categories.items():
            count = Item.objects.filter(item_code__startswith=prefix).count()
            self.stdout.write(f'{category_name}: {count} 件')
        
        # 出荷依頼の配送日別統計
        from django.db.models import Count
        delivery_stats = ShippingOrder.objects.values('delivery_deadline').annotate(
            count=Count('id')
        ).order_by('delivery_deadline')
        
        self.stdout.write('\n=== 配送日別出荷依頼数 ===')
        for stat in delivery_stats:
            date_str = stat['delivery_deadline'].strftime('%Y-%m-%d')
            self.stdout.write(f'{date_str}: {stat["count"]} 件')

    def _create_items(self):
        """商品データ作成"""
        items_data = [
            # 電子機器・PC関連
            {'item_code': 'PC001', 'name': 'ノートPC（13インチ）', 'width': 30, 'depth': 21, 'height': 2, 'weight': 1.3},
            {'item_code': 'PC002', 'name': 'ノートPC（15インチ）', 'width': 35, 'depth': 24, 'height': 3, 'weight': 2.1},
            {'item_code': 'PC003', 'name': 'デスクトップPC', 'width': 40, 'depth': 35, 'height': 40, 'weight': 8.0},
            {'item_code': 'PC004', 'name': 'タブレット', 'width': 25, 'depth': 17, 'height': 1, 'weight': 0.5},
            {'item_code': 'PC005', 'name': 'モニター（24インチ）', 'width': 54, 'depth': 21, 'height': 32, 'weight': 4.5},
            {'item_code': 'PC006', 'name': 'モニター（27インチ）', 'width': 61, 'depth': 23, 'height': 36, 'weight': 6.2},
            {'item_code': 'PC007', 'name': 'キーボード', 'width': 44, 'depth': 13, 'height': 3, 'weight': 0.8},
            {'item_code': 'PC008', 'name': 'マウス', 'width': 12, 'depth': 6, 'height': 4, 'weight': 0.1},
            {'item_code': 'PC009', 'name': 'プリンター（インクジェット）', 'width': 45, 'depth': 30, 'height': 15, 'weight': 5.5},
            {'item_code': 'PC010', 'name': 'プリンター（レーザー）', 'width': 40, 'depth': 38, 'height': 26, 'weight': 12.0},
            
            # スマートフォン・周辺機器
            {'item_code': 'SP001', 'name': 'スマートフォン', 'width': 15, 'depth': 7, 'height': 1, 'weight': 0.2},
            {'item_code': 'SP002', 'name': 'スマートフォンケース', 'width': 16, 'depth': 8, 'height': 2, 'weight': 0.1},
            {'item_code': 'SP003', 'name': '充電器', 'width': 8, 'depth': 5, 'height': 3, 'weight': 0.3},
            {'item_code': 'SP004', 'name': 'ワイヤレスイヤホン', 'width': 10, 'depth': 6, 'height': 4, 'weight': 0.1},
            {'item_code': 'SP005', 'name': 'モバイルバッテリー', 'width': 14, 'depth': 7, 'height': 2, 'weight': 0.4},
            
            # 書籍・文具
            {'item_code': 'BK001', 'name': '文庫本', 'width': 11, 'depth': 16, 'height': 1, 'weight': 0.2},
            {'item_code': 'BK002', 'name': '単行本', 'width': 13, 'depth': 19, 'height': 2, 'weight': 0.4},
            {'item_code': 'BK003', 'name': '雑誌', 'width': 21, 'depth': 28, 'height': 1, 'weight': 0.3},
            {'item_code': 'BK004', 'name': 'ノート', 'width': 18, 'depth': 25, 'height': 1, 'weight': 0.2},
            {'item_code': 'BK005', 'name': 'ファイル', 'width': 23, 'depth': 31, 'height': 3, 'weight': 0.5},
            
            # 家電製品
            {'item_code': 'HE001', 'name': '冷蔵庫（大型）', 'width': 60, 'depth': 65, 'height': 180, 'weight': 80.0},
            {'item_code': 'HE002', 'name': '冷蔵庫（中型）', 'width': 55, 'depth': 58, 'height': 150, 'weight': 60.0},
            {'item_code': 'HE003', 'name': '洗濯機', 'width': 60, 'depth': 60, 'height': 105, 'weight': 45.0},
            {'item_code': 'HE004', 'name': '電子レンジ', 'width': 48, 'depth': 39, 'height': 30, 'weight': 15.0},
            {'item_code': 'HE005', 'name': '炊飯器', 'width': 25, 'depth': 35, 'height': 20, 'weight': 4.0},
            {'item_code': 'HE006', 'name': '掃除機', 'width': 25, 'depth': 30, 'height': 20, 'weight': 5.0},
            {'item_code': 'HE007', 'name': 'エアコン室外機', 'width': 80, 'depth': 30, 'height': 55, 'weight': 35.0},
            {'item_code': 'HE008', 'name': 'テレビ（32インチ）', 'width': 73, 'depth': 17, 'height': 43, 'weight': 8.5},
            {'item_code': 'HE009', 'name': 'テレビ（55インチ）', 'width': 123, 'depth': 25, 'height': 71, 'weight': 18.0},
            {'item_code': 'HE010', 'name': '空気清浄機', 'width': 40, 'depth': 23, 'height': 61, 'weight': 7.5},
            
            # 生活用品・日用品
            {'item_code': 'LI001', 'name': 'ティッシュボックス', 'width': 23, 'depth': 11, 'height': 6, 'weight': 0.5},
            {'item_code': 'LI002', 'name': 'トイレットペーパー（12ロール）', 'width': 25, 'depth': 25, 'height': 35, 'weight': 3.0},
            {'item_code': 'LI003', 'name': '洗剤ボトル', 'width': 8, 'depth': 8, 'height': 20, 'weight': 1.2},
            {'item_code': 'LI004', 'name': 'シャンプーボトル', 'width': 7, 'depth': 7, 'height': 18, 'weight': 0.8},
            {'item_code': 'LI005', 'name': 'タオルセット', 'width': 30, 'depth': 20, 'height': 10, 'weight': 1.5},
            
            # 衣類・アパレル
            {'item_code': 'CL001', 'name': 'Tシャツ', 'width': 25, 'depth': 20, 'height': 3, 'weight': 0.2},
            {'item_code': 'CL002', 'name': 'ジーンズ', 'width': 30, 'depth': 25, 'height': 5, 'weight': 0.7},
            {'item_code': 'CL003', 'name': 'ジャケット', 'width': 35, 'depth': 30, 'height': 8, 'weight': 1.0},
            {'item_code': 'CL004', 'name': '靴', 'width': 30, 'depth': 18, 'height': 12, 'weight': 1.2},
            {'item_code': 'CL005', 'name': 'バッグ', 'width': 40, 'depth': 15, 'height': 30, 'weight': 0.8},
            
            # 食品・飲料
            {'item_code': 'FD001', 'name': 'ペットボトル（500ml）', 'width': 6, 'depth': 6, 'height': 20, 'weight': 0.6},
            {'item_code': 'FD002', 'name': '缶詰', 'width': 7, 'depth': 7, 'height': 10, 'weight': 0.4},
            {'item_code': 'FD003', 'name': 'レトルトパック', 'width': 15, 'depth': 10, 'height': 2, 'weight': 0.2},
            {'item_code': 'FD004', 'name': '米袋（5kg）', 'width': 30, 'depth': 20, 'height': 8, 'weight': 5.0},
            {'item_code': 'FD005', 'name': '調味料セット', 'width': 25, 'depth': 15, 'height': 20, 'weight': 2.0},
            
            # 段ボール・梱包材
            {'item_code': 'PK001', 'name': '段ボール箱（SS）', 'width': 20, 'depth': 15, 'height': 10, 'weight': 1.0},
            {'item_code': 'PK002', 'name': '段ボール箱（S）', 'width': 30, 'depth': 20, 'height': 15, 'weight': 2.0},
            {'item_code': 'PK003', 'name': '段ボール箱（M）', 'width': 40, 'depth': 30, 'height': 20, 'weight': 3.5},
            {'item_code': 'PK004', 'name': '段ボール箱（L）', 'width': 50, 'depth': 40, 'height': 30, 'weight': 5.0},
            {'item_code': 'PK005', 'name': '段ボール箱（LL）', 'width': 60, 'depth': 45, 'height': 35, 'weight': 8.0},
            {'item_code': 'PK006', 'name': '緩衝材', 'width': 50, 'depth': 30, 'height': 20, 'weight': 1.0},
            
            # スポーツ・趣味用品
            {'item_code': 'SP101', 'name': 'サッカーボール', 'width': 22, 'depth': 22, 'height': 22, 'weight': 0.4},
            {'item_code': 'SP102', 'name': 'テニスラケット', 'width': 68, 'depth': 25, 'height': 5, 'weight': 0.3},
            {'item_code': 'SP103', 'name': 'ゴルフクラブセット', 'width': 120, 'depth': 25, 'height': 15, 'weight': 8.0},
            {'item_code': 'SP104', 'name': 'フィットネスマット', 'width': 180, 'depth': 60, 'height': 5, 'weight': 2.0},
            {'item_code': 'SP105', 'name': 'ダンベル（5kg）', 'width': 15, 'depth': 15, 'height': 20, 'weight': 5.0},
        ]
        
        for item_data in items_data:
            Item.objects.get_or_create(
                item_code=item_data['item_code'],
                defaults=item_data
            )
        
        self.stdout.write(f'商品データ {len(items_data)} 件を作成しました。')

    def _create_shippers(self):
        """荷主データ作成"""
        shippers_data = [
            {
                'shipper_code': 'S001',
                'name': 'ABC電機株式会社',
                'address': '東京都千代田区丸の内1-1-1',
                'contact_phone': '03-1234-5678',
                'contact_email': 'contact@abc-denki.co.jp'
            },
            {
                'shipper_code': 'S002', 
                'name': '山田書店チェーン',
                'address': '東京都新宿区新宿3-1-1',
                'contact_phone': '03-2345-6789',
                'contact_email': 'info@yamada-books.co.jp'
            },
            {
                'shipper_code': 'S003',
                'name': '鈴木家電販売',
                'address': '東京都渋谷区渋谷2-1-1',
                'contact_phone': '03-3456-7890',
                'contact_email': 'sales@suzuki-kaden.co.jp'
            },
            {
                'shipper_code': 'S004',
                'name': '物流太郎商事',
                'address': '東京都港区赤坂1-1-1',
                'contact_phone': '03-4567-8901',
                'contact_email': 'order@buturyu-taro.co.jp'
            },
            {
                'shipper_code': 'S005',
                'name': 'テックワールド株式会社',
                'address': '東京都品川区大崎1-2-3',
                'contact_phone': '03-5555-1111',
                'contact_email': 'sales@techworld.co.jp'
            },
            {
                'shipper_code': 'S006',
                'name': 'ライフスタイル雑貨',
                'address': '東京都目黒区中目黒2-3-4',
                'contact_phone': '03-6666-2222',
                'contact_email': 'info@lifestyle-goods.co.jp'
            },
            {
                'shipper_code': 'S007',
                'name': 'スポーツプラザ田中',
                'address': '東京都世田谷区三軒茶屋3-4-5',
                'contact_phone': '03-7777-3333',
                'contact_email': 'order@sports-tanaka.co.jp'
            },
            {
                'shipper_code': 'S008',
                'name': 'フード&ドリンク卸売',
                'address': '東京都大田区蒲田4-5-6',
                'contact_phone': '03-8888-4444',
                'contact_email': 'wholesale@food-drink.co.jp'
            },
            {
                'shipper_code': 'S009',
                'name': 'ファッション倉庫',
                'address': '東京都台東区上野5-6-7',
                'contact_phone': '03-9999-5555',
                'contact_email': 'fashion@warehouse.co.jp'
            },
            {
                'shipper_code': 'S010',
                'name': 'ホーム&ガーデン',
                'address': '神奈川県横浜市中区元町6-7-8',
                'contact_phone': '045-1111-6666',
                'contact_email': 'contact@home-garden.co.jp'
            }
        ]
        
        for shipper_data in shippers_data:
            Shipper.objects.get_or_create(
                shipper_code=shipper_data['shipper_code'],
                defaults=shipper_data
            )
        
        self.stdout.write(f'荷主データ {len(shippers_data)} 件を作成しました。')

    def _create_destinations(self):
        """配送先データ作成"""
        destinations_data = [
            # 東京23区内
            {
                'name': '東京本社ビル',
                'address': '東京都千代田区丸の内1-1-1',
                'postal_code': '100-0005',
                'latitude': 35.6815,
                'longitude': 139.7646,
                'contact_phone': '03-1000-0001'
            },
            {
                'name': '新宿支店',
                'address': '東京都新宿区西新宿2-8-1',
                'postal_code': '160-0023',
                'latitude': 35.6896,
                'longitude': 139.6917,
                'contact_phone': '03-1000-0002'
            },
            {
                'name': '渋谷営業所',
                'address': '東京都渋谷区渋谷3-15-3',
                'postal_code': '150-0002',
                'latitude': 35.6598,
                'longitude': 139.7036,
                'contact_phone': '03-1000-0003'
            },
            {
                'name': '品川物流センター',
                'address': '東京都品川区東品川4-12-8',
                'postal_code': '140-0002',
                'latitude': 35.6052,
                'longitude': 139.7343,
                'contact_phone': '03-1000-0004'
            },
            {
                'name': '池袋店舗',
                'address': '東京都豊島区南池袋1-28-1',
                'postal_code': '171-0022',
                'latitude': 35.7295,
                'longitude': 139.7109,
                'contact_phone': '03-1000-0005'
            },
            {
                'name': '上野配送センター',
                'address': '東京都台東区上野7-1-1',
                'postal_code': '110-0005',
                'latitude': 35.7071,
                'longitude': 139.7731,
                'contact_phone': '03-1000-0006'
            },
            {
                'name': '銀座店',
                'address': '東京都中央区銀座4-6-16',
                'postal_code': '104-0061',
                'latitude': 35.6719,
                'longitude': 139.7653,
                'contact_phone': '03-1000-0007'
            },
            {
                'name': '六本木オフィス',
                'address': '東京都港区六本木6-10-1',
                'postal_code': '106-0032',
                'latitude': 35.6627,
                'longitude': 139.7310,
                'contact_phone': '03-1000-0008'
            },
            {
                'name': '秋葉原電気街店',
                'address': '東京都千代田区外神田1-15-1',
                'postal_code': '101-0021',
                'latitude': 35.6984,
                'longitude': 139.7731,
                'contact_phone': '03-1000-0009'
            },
            {
                'name': '浅草店',
                'address': '東京都台東区浅草1-36-3',
                'postal_code': '111-0032',
                'latitude': 35.7148,
                'longitude': 139.7967,
                'contact_phone': '03-1000-0010'
            },
            {
                'name': '恵比寿営業所',
                'address': '東京都渋谷区恵比寿1-19-19',
                'postal_code': '150-0013',
                'latitude': 35.6465,
                'longitude': 139.7100,
                'contact_phone': '03-1000-0011'
            },
            {
                'name': '表参道店',
                'address': '東京都港区北青山3-6-12',
                'postal_code': '107-0061',
                'latitude': 35.6652,
                'longitude': 139.7127,
                'contact_phone': '03-1000-0012'
            },
            
            # 神奈川県
            {
                'name': '横浜みなとみらい支社',
                'address': '神奈川県横浜市西区みなとみらい2-2-1',
                'postal_code': '220-0012',
                'latitude': 35.4593,
                'longitude': 139.6317,
                'contact_phone': '045-1000-0001'
            },
            {
                'name': '川崎工場',
                'address': '神奈川県川崎市川崎区東田町8-1',
                'postal_code': '210-0005',
                'latitude': 35.5308,
                'longitude': 139.7029,
                'contact_phone': '044-1000-0002'
            },
            {
                'name': '藤沢配送センター',
                'address': '神奈川県藤沢市藤沢588',
                'postal_code': '251-0052',
                'latitude': 35.3389,
                'longitude': 139.4914,
                'contact_phone': '0466-1000-0003'
            },
            {
                'name': '厚木倉庫',
                'address': '神奈川県厚木市中町3-17-17',
                'postal_code': '243-0018',
                'latitude': 35.4409,
                'longitude': 139.3661,
                'contact_phone': '046-1000-0004'
            },
            
            # 埼玉県
            {
                'name': '大宮営業所',
                'address': '埼玉県さいたま市大宮区桜木町1-7-5',
                'postal_code': '330-0854',
                'latitude': 35.9069,
                'longitude': 139.6224,
                'contact_phone': '048-1000-0001'
            },
            {
                'name': '川越配送センター',
                'address': '埼玉県川越市脇田本町15-13',
                'postal_code': '350-1123',
                'latitude': 35.9088,
                'longitude': 139.4851,
                'contact_phone': '049-1000-0002'
            },
            {
                'name': '越谷物流拠点',
                'address': '埼玉県越谷市南越谷1-16-1',
                'postal_code': '343-0845',
                'latitude': 35.8817,
                'longitude': 139.7917,
                'contact_phone': '048-1000-0003'
            },
            
            # 千葉県
            {
                'name': '千葉支店',
                'address': '千葉県千葉市中央区富士見2-3-1',
                'postal_code': '260-0015',
                'latitude': 35.6069,
                'longitude': 140.1233,
                'contact_phone': '043-1000-0001'
            },
            {
                'name': '船橋倉庫',
                'address': '千葉県船橋市本町1-3-1',
                'postal_code': '273-0005',
                'latitude': 35.6947,
                'longitude': 139.9845,
                'contact_phone': '047-1000-0002'
            },
            {
                'name': '成田配送センター',
                'address': '千葉県成田市花崎町760',
                'postal_code': '286-0033',
                'latitude': 35.7650,
                'longitude': 140.3178,
                'contact_phone': '0476-1000-0003'
            },
            
            # 東京多摩地区
            {
                'name': '立川営業所',
                'address': '東京都立川市曙町2-4-4',
                'postal_code': '190-0012',
                'latitude': 35.6977,
                'longitude': 139.4138,
                'contact_phone': '042-1000-0001'
            },
            {
                'name': '八王子配送センター',
                'address': '東京都八王子市旭町9-1',
                'postal_code': '192-0083',
                'latitude': 35.6558,
                'longitude': 139.3386,
                'contact_phone': '042-1000-0002'
            }
        ]
        
        for dest_data in destinations_data:
            Destination.objects.get_or_create(
                name=dest_data['name'],
                defaults=dest_data
            )
        
        self.stdout.write(f'配送先データ {len(destinations_data)} 件を作成しました。')

    def _create_trucks(self):
        """トラックデータ作成"""
        trucks_data = [
            {
                'width': 200, 'depth': 400, 'height': 200, 'payload': 2000,
                'shipping_company': 'ヤマト運輸', 'truck_class': '2t', 'model': '小型トラック'
            },
            {
                'width': 220, 'depth': 450, 'height': 220, 'payload': 4000,
                'shipping_company': '佐川急便', 'truck_class': '4t', 'model': '中型トラック'
            },
            {
                'width': 240, 'depth': 500, 'height': 240, 'payload': 6000,
                'shipping_company': '日本通運', 'truck_class': '6t', 'model': '大型トラック'
            },
            {
                'width': 200, 'depth': 400, 'height': 200, 'payload': 2000,
                'shipping_company': '福山通運', 'truck_class': '2t', 'model': '小型トラック'
            },
            {
                'width': 220, 'depth': 450, 'height': 220, 'payload': 4000,
                'shipping_company': 'セイノー運輸', 'truck_class': '4t', 'model': '中型トラック'
            }
        ]
        
        for truck_data in trucks_data:
            Truck.objects.create(**truck_data)
        
        self.stdout.write(f'トラックデータ {len(trucks_data)} 件を作成しました。')

    def _create_shipping_orders(self):
        """出荷依頼データ作成"""
        shippers = list(Shipper.objects.all())
        destinations = list(Destination.objects.all())
        items = list(Item.objects.all())
        
        # 明日から14日間のデータを作成
        base_date = date.today() + timedelta(days=1)
        
        order_count = 0
        
        # 150件の出荷依頼を作成
        for i in range(150):
            delivery_date = base_date + timedelta(days=random.randint(0, 13))
            
            order = ShippingOrder.objects.create(
                order_number=f'ORD{(i+1):05d}',  # 5桁の注文番号
                shipper=random.choice(shippers),
                destination=random.choice(destinations),
                delivery_deadline=delivery_date
            )
            
            # 各注文に1-8個の異なる商品を追加（より現実的な数量）
            num_different_items = random.randint(1, 8)
            selected_items = random.sample(items, min(num_different_items, len(items)))
            
            for item in selected_items:
                # 商品の種類によって数量を調整
                if item.item_code.startswith('HE'):  # 家電は少なめ
                    quantity = random.randint(1, 3)
                elif item.item_code.startswith('PC'):  # PC関連も少なめ
                    quantity = random.randint(1, 5)
                elif item.item_code.startswith('BK'):  # 書籍は多め
                    quantity = random.randint(5, 50)
                elif item.item_code.startswith('PK'):  # 梱包材は多め
                    quantity = random.randint(10, 100)
                elif item.item_code.startswith('LI'):  # 生活用品
                    quantity = random.randint(2, 20)
                elif item.item_code.startswith('FD'):  # 食品
                    quantity = random.randint(5, 30)
                elif item.item_code.startswith('CL'):  # 衣類
                    quantity = random.randint(3, 15)
                elif item.item_code.startswith('SP'):  # スマホ関連
                    quantity = random.randint(1, 10)
                else:  # その他
                    quantity = random.randint(1, 20)
                
                OrderItem.objects.create(
                    shipping_order=order,
                    item=item,
                    quantity=quantity
                )
            
            order_count += 1
            
            # 進捗表示
            if (i + 1) % 25 == 0:
                self.stdout.write(f'出荷依頼 {i + 1}/150 件作成完了...')
        
        self.stdout.write(f'出荷依頼データ {order_count} 件を作成しました。')
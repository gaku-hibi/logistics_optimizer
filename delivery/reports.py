"""
レポート生成機能
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from io import BytesIO
import os

from .models import DeliveryPlan


# 日本語フォント設定
def setup_japanese_fonts():
    """日本語フォントを設定"""
    try:
        # Docker環境のNoto Sans CJKフォントを優先的に探す
        noto_paths = [
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/truetype/noto-cjk/NotoSansCJK-Regular.ttc',
            '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc',
            '/usr/share/fonts/truetype/noto/NotoSansJP-Regular.otf',
            '/usr/share/fonts/opentype/noto/NotoSansJP[wght].ttf'
        ]
        
        for font_path in noto_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('NotoSansCJK', font_path))
                    return 'NotoSansCJK'
                except Exception as e:
                    print(f"フォント登録失敗 {font_path}: {e}")
                    continue
        
        # CID フォントを試す
        try:
            pdfmetrics.registerFont(UnicodeCIDFont('HeiseiMin-W3'))
            return 'HeiseiMin-W3'
        except:
            try:
                pdfmetrics.registerFont(UnicodeCIDFont('HeiseiKakuGo-W5'))
                return 'HeiseiKakuGo-W5'
            except:
                pass
        
        # その他のシステムフォントを探す
        other_font_paths = [
            '/System/Library/Fonts/Hiragino Sans GB.ttc',  # macOS
            '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc',  # macOS
            'C:/Windows/Fonts/msmincho.ttc',  # Windows
            'C:/Windows/Fonts/msgothic.ttc',  # Windows
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux
        ]
        
        for font_path in other_font_paths:
            if os.path.exists(font_path):
                try:
                    pdfmetrics.registerFont(TTFont('SystemFont', font_path))
                    return 'SystemFont'
                except Exception as e:
                    continue
        
        # 全て失敗した場合はHelveticaを使用（警告）
        print("警告: 日本語フォントが見つかりません。Helveticaを使用します。")
        return 'Helvetica'
        
    except Exception as e:
        print(f"フォント設定エラー: {e}")
        return 'Helvetica'


def generate_plan_report(plan: DeliveryPlan) -> BytesIO:
    """配送計画レポートを生成"""
    buffer = BytesIO()
    
    # 日本語フォント設定
    japanese_font = setup_japanese_fonts()
    print(f"使用フォント: {japanese_font}")  # デバッグ用
    
    # PDFドキュメント作成
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    # スタイル設定
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Title'],
        fontSize=16,
        spaceAfter=20*mm,
        alignment=1,  # 中央揃え
        fontName=japanese_font
    )
    
    heading_style = ParagraphStyle(
        'HeadingStyle',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=6*mm,
        fontName=japanese_font
    )
    
    # コンテンツ作成
    content = []
    
    # タイトル
    title = Paragraph(f"配送計画書 - Plan #{plan.id}", title_style)
    content.append(title)
    
    # 基本情報
    content.append(Paragraph("■ 基本情報", heading_style))
    
    basic_info = [
        ['配送日', plan.plan_date.strftime('%Y年%m月%d日')],
        ['出発時刻', plan.departure_time.strftime('%H:%M')],
        ['使用車両', f"{plan.truck.shipping_company} {plan.truck.truck_class}"],
        ['積載重量', f"{plan.total_weight:.1f} kg"],
        ['積載体積', f"{plan.total_volume:,} cm³"],
    ]
    
    if plan.route_distance_km:
        basic_info.append(['走行距離', f"{plan.route_distance_km:.1f} km"])
    
    basic_table = Table(basic_info, colWidths=[40*mm, 60*mm])
    basic_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), japanese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(basic_table)
    content.append(Spacer(1, 10*mm))
    
    # 配送先一覧
    content.append(Paragraph("■ 配送先一覧", heading_style))
    
    delivery_data = [['順序', '出荷依頼番号', '配送先', '住所', '到着予定']]
    
    for detail in plan.order_details.all():
        delivery_data.append([
            str(detail.delivery_sequence),
            detail.shipping_order.order_number,
            detail.shipping_order.destination.name,
            detail.shipping_order.destination.address,
            detail.estimated_arrival.strftime('%H:%M')
        ])
    
    delivery_table = Table(delivery_data, colWidths=[15*mm, 30*mm, 40*mm, 60*mm, 20*mm])
    delivery_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), japanese_font),
        ('FONTNAME', (0, 1), (-1, -1), japanese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(delivery_table)
    content.append(Spacer(1, 10*mm))
    
    # 積載商品一覧
    content.append(Paragraph("■ 積載商品一覧", heading_style))
    
    item_data = [['商品名', '数量', '重量', '配置位置']]
    
    for load in plan.item_loads.all():
        item_data.append([
            load.item.name,
            str(load.quantity),
            f"{load.item.weight * load.quantity:.1f} kg" if load.item.weight else "N/A",
            f"({load.position_x}, {load.position_y})"
        ])
    
    item_table = Table(item_data, colWidths=[60*mm, 20*mm, 25*mm, 30*mm])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), japanese_font),
        ('FONTNAME', (0, 1), (-1, -1), japanese_font),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    content.append(item_table)
    
    # PDF生成
    doc.build(content)
    
    buffer.seek(0)
    return buffer
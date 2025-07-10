from django.core.management.base import BaseCommand
import os
import glob


class Command(BaseCommand):
    help = 'システムで利用可能なフォントファイルを確認します'

    def handle(self, *args, **options):
        font_dirs = [
            '/usr/share/fonts/',
            '/System/Library/Fonts/',
            'C:/Windows/Fonts/',
        ]
        
        for font_dir in font_dirs:
            if os.path.exists(font_dir):
                self.stdout.write(f"\n=== {font_dir} ===")
                
                # フォントファイルを探す
                font_patterns = ['*.ttf', '*.ttc', '*.otf']
                for pattern in font_patterns:
                    font_files = glob.glob(os.path.join(font_dir, '**', pattern), recursive=True)
                    for font_file in font_files:
                        if any(keyword in font_file.lower() for keyword in ['cjk', 'jp', 'japanese', 'noto', 'sans']):
                            self.stdout.write(f"  {font_file}")
        
        # reportlabで使用可能なCIDフォントもテスト
        self.stdout.write(f"\n=== CIDフォント テスト ===")
        try:
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.cidfonts import UnicodeCIDFont
            
            cid_fonts = ['HeiseiMin-W3', 'HeiseiKakuGo-W5']
            for font_name in cid_fonts:
                try:
                    pdfmetrics.registerFont(UnicodeCIDFont(font_name))
                    self.stdout.write(f"  ✓ {font_name}")
                except:
                    self.stdout.write(f"  ✗ {font_name}")
        except Exception as e:
            self.stdout.write(f"  エラー: {e}")
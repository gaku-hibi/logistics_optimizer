from django import forms
from django.core.exceptions import ValidationError
import csv
import io


class CSVUploadForm(forms.Form):
    csv_file = forms.FileField(
        label='CSVファイル',
        help_text='UTF-8エンコーディングのCSVファイルを選択してください',
        widget=forms.FileInput(attrs={'accept': '.csv', 'class': 'form-control'})
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data['csv_file']
        
        # ファイル拡張子チェック
        if not csv_file.name.endswith('.csv'):
            raise ValidationError('CSVファイルを選択してください。')
        
        # ファイルサイズチェック（10MB以下）
        if csv_file.size > 10 * 1024 * 1024:
            raise ValidationError('ファイルサイズは10MB以下にしてください。')
        
        # CSVファイルの読み込みテスト
        try:
            decoded_file = csv_file.read().decode('utf-8')
            io_string = io.StringIO(decoded_file)
            reader = csv.DictReader(io_string)
            
            # 少なくとも1行のデータがあるかチェック
            first_row = next(reader, None)
            if not first_row:
                raise ValidationError('CSVファイルにデータが含まれていません。')
            
            # ファイルポインタを先頭に戻す
            csv_file.seek(0)
            
        except UnicodeDecodeError:
            raise ValidationError('ファイルのエンコーディングが正しくありません。UTF-8で保存してください。')
        except Exception as e:
            raise ValidationError(f'CSVファイルの読み込みエラー: {str(e)}')
        
        return csv_file


class ProductCSVUploadForm(CSVUploadForm):
    """商品CSV取り込み用フォーム"""
    
    def clean_csv_file(self):
        csv_file = super().clean_csv_file()
        
        # 必須カラムのチェック
        required_columns = {
            'shipper_name', 'name', 'width', 'height', 'depth', 
            'weight', 'destination_address', 'delivery_deadline'
        }
        
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        first_row = next(reader, None)
        if first_row:
            missing_columns = required_columns - set(first_row.keys())
            if missing_columns:
                raise ValidationError(
                    f'必須カラムが不足しています: {", ".join(missing_columns)}'
                )
        
        csv_file.seek(0)
        return csv_file


class TruckCSVUploadForm(CSVUploadForm):
    """トラックCSV取り込み用フォーム"""
    
    def clean_csv_file(self):
        csv_file = super().clean_csv_file()
        
        # 必須カラムのチェック
        required_columns = {'name', 'bed_width', 'bed_depth', 'max_weight'}
        
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        first_row = next(reader, None)
        if first_row:
            missing_columns = required_columns - set(first_row.keys())
            if missing_columns:
                raise ValidationError(
                    f'必須カラムが不足しています: {", ".join(missing_columns)}'
                )
        
        csv_file.seek(0)
        return csv_file
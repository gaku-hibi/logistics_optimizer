from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Field
from .models import ShippingOrder, OrderItem, Truck, Item, Shipper, Destination


class ShippingOrderForm(forms.ModelForm):
    class Meta:
        model = ShippingOrder
        fields = ['order_number', 'shipper', 'destination', 'delivery_deadline']
        widgets = {
            'delivery_deadline': forms.DateInput(attrs={'type': 'date'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('order_number', css_class='form-group col-md-6 mb-0'),
                Column('delivery_deadline', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('shipper', css_class='form-group col-md-6 mb-0'),
                Column('destination', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', '保存', css_class='btn btn-primary')
        )


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['item', 'quantity']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('item', css_class='form-group col-md-8 mb-0'),
                Column('quantity', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            )
        )


class TruckForm(forms.ModelForm):
    class Meta:
        model = Truck
        fields = ['width', 'depth', 'height', 'payload', 'shipping_company', 'truck_class', 'model']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('shipping_company', css_class='form-group col-md-6 mb-0'),
                Column('truck_class', css_class='form-group col-md-3 mb-0'),
                Column('model', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('width', css_class='form-group col-md-3 mb-0'),
                Column('depth', css_class='form-group col-md-3 mb-0'),
                Column('height', css_class='form-group col-md-3 mb-0'),
                Column('payload', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', '保存', css_class='btn btn-primary')
        )


class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['item_code', 'name', 'width', 'depth', 'height', 'weight', 'parts_count']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('item_code', css_class='form-group col-md-6 mb-0'),
                Column('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Row(
                Column('width', css_class='form-group col-md-3 mb-0'),
                Column('depth', css_class='form-group col-md-3 mb-0'),
                Column('height', css_class='form-group col-md-3 mb-0'),
                Column('weight', css_class='form-group col-md-3 mb-0'),
                css_class='form-row'
            ),
            'parts_count',
            Submit('submit', '保存', css_class='btn btn-primary')
        )


class ShipperForm(forms.ModelForm):
    class Meta:
        model = Shipper
        fields = ['shipper_code', 'name', 'address', 'contact_phone', 'contact_email']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('shipper_code', css_class='form-group col-md-6 mb-0'),
                Column('name', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('contact_phone', css_class='form-group col-md-6 mb-0'),
                Column('contact_email', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', '保存', css_class='btn btn-primary')
        )


class DestinationForm(forms.ModelForm):
    class Meta:
        model = Destination
        fields = ['name', 'address', 'postal_code', 'latitude', 'longitude', 'contact_phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            Row(
                Column('name', css_class='form-group col-md-6 mb-0'),
                Column('postal_code', css_class='form-group col-md-6 mb-0'),
                css_class='form-row'
            ),
            'address',
            Row(
                Column('latitude', css_class='form-group col-md-4 mb-0'),
                Column('longitude', css_class='form-group col-md-4 mb-0'),
                Column('contact_phone', css_class='form-group col-md-4 mb-0'),
                css_class='form-row'
            ),
            Submit('submit', '保存', css_class='btn btn-primary')
        )


class OptimizeForm(forms.Form):
    target_date = forms.DateField(
        label='対象日',
        widget=forms.DateInput(attrs={'type': 'date'}),
        help_text='最適化を実行する配送日を選択してください'
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.layout = Layout(
            'target_date',
            Submit('submit', '最適化実行', css_class='btn btn-success')
        )
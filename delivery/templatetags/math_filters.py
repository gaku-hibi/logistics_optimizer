from django import template

register = template.Library()

@register.filter
def mul(value, arg):
    """値を引数で掛け算する"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0
from decimal import Decimal
from django import template

register = template.Library()

@register.filter
def pen(value):
    if value is None:
        return '—'
    return f'S/ {Decimal(value):,.2f}'

@register.filter
def num(value):
    if value is None:
        return '—'
    return f'{Decimal(value):,.0f}'

@register.filter
def quantity(value):
    return format(Decimal(value).normalize(), 'f')

@register.filter
def initial(value):
    return str(value or 'M')[:1].upper()

@register.simple_tag(takes_context=True)
def query_url(context, **kwargs):
    query = context['request'].GET.copy()
    for key, value in kwargs.items():
        query[key] = value
    return '?' + query.urlencode()

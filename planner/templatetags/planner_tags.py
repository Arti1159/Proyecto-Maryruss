from decimal import Decimal, InvalidOperation
from django import template
register=template.Library()
@register.filter
def plan_money(value,currency='PEN'):
    if value is None:return 'Por confirmar'
    try:amount=Decimal(str(value))
    except InvalidOperation:return '—'
    symbol={'PEN':'S/','USD':'US$','EUR':'€'}.get(currency,currency)
    return f'{symbol} {amount:,.2f}'

@register.filter
def plan_rate(value,currency='PEN'):
    if value is None:return 'Por confirmar'
    try:text=f'{Decimal(str(value)):,.4f}'
    except InvalidOperation:return '—'
    while text.endswith('0') and len(text.rsplit('.',1)[1])>2:text=text[:-1]
    symbol={'PEN':'S/','USD':'US$','EUR':'€'}.get(currency,currency)
    return symbol+' '+text

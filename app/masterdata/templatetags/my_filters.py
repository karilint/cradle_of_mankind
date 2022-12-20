from django import template
from masterdata.models import MasterData

register = template.Library()


@register.filter(name='range')
def _range(number):
    return range(1, number+1)


@register.filter(name='split')
def _split(string):
    return string.split()


@register.filter(name='getattr')
def _getattr(obj, attr):
    if not obj:
        return ''
    return getattr(obj, attr)


@register.filter(name='to_string')
def to_string(master_data):
    """Takes a master data object (or list of them) and returns 
    a string where all their unique values have been combined.
    """
    if isinstance(master_data, MasterData):
        return master_data.value.value
    if isinstance(master_data, list):
        values = set()
        for md in master_data:
            if md.value.value:
                values.add(md.value.value)
        return ' | '.join(values)

    return ""

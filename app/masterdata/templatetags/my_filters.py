from django import template

register = template.Library()


@register.filter(name='range')
def _range(number):
    return range(1, number+1)


@register.filter(name='split')
def _split(string):
    return string.split()


@register.filter(name='to_string')
def to_string(master_data):
    """Takes a master data object and returns a string where all the 
    unique master values have been combined together with '|' symbol.
    """

    values = set()
    for master_value in master_data.master_values.all():
        values.add(master_value.value)
    return ' | '.join(values)

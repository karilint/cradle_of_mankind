from django import template

register = template.Library()


@register.filter(name='range')
def _range(number):
    return range(1, number+1)


@register.filter(name='to_string')
def to_string(master_data):
    """Takes a master data object and returns a string where all the 
    unique master values have been combined together with '|' symbol.
    """

    values = set()
    for master_value in master_data.mastervalue_set.all():
        values.add(master_value.value)
    return ' | '.join(values)

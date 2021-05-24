from django import template

register = template.Library()


@register.filter(name='range')
def _range(number):
    return range(1, number+1)

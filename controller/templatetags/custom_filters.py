from django import template
register = template.Library()

@register.filter
def dict_get(d, key):
    return d.get(key, '')

@register.filter(name='get_item')
def get_item(dictionary, key):
    """Fetches a value from a dictionary using a dynamic key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key, [])

@register.filter
def index(sequence, position):
    try:
        return sequence[position]
    except:
        return None

@register.filter
def to(start, end):
    """Creates a range for looping in template: {% for i in 1|to:program.slots %}"""
    return range(start, end+1)

@register.filter
def dict_get(d, key):
    """Get value from dict by key"""
    return d.get(key, [])

@register.filter
def index(sequence, i):
    """Get index from a list"""
    try:
        return sequence[i]
    except (IndexError, TypeError):
        return None

@register.filter
def get_range(value):
    """Return a range object (loops that many times)."""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(0)
from django import template

register = template.Library()


@register.filter
def youtube_id(value):
    """YouTube havolasidan video ID ni ajratib oladi."""
    if "=" in value:
        return value.split('=')[-1]
    return value

'''Tags for menu '''

from django import template
from django.conf import settings

from .. import models

register = template.Library()


@register.simple_tag(takes_context=True)
def menu_items(context, var_name, alias):
    '''Put a list of menu items related to menu with specified alias into
    context with selected variable name
    '''
    translations = models.PageTranslation.objects.filter(language__code=settings.LANGUAGE_CODE,
                                                         page__menuitem__menu__alias=alias)\
                                .order_by('page__menuitem__order')
    context[var_name] = translations
    return ''

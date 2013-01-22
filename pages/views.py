'''View that renders the page
'''
from django import shortcuts, template

from . import models


def get_page_data(request, slug=None):
    '''Get all data needed for page
    '''
    filters = ({'alias': slug, 'is_active': True} if slug
                else {'page__is_default': True})
    page = shortcuts.get_object_or_404(models.PageTranslation, **filters)
    template_name = page.layout.template
    articles = models.PageArticle.objects.filter(page=page,
                            layout=page.layout).select_related('place_alias')
    try:
        alt_url = page.alt_url
    except:
        alt_url = None
    print alt_url
    blocks = {article.place.alias: article for article in articles}
    return template_name, {'page': page, 'blocks': blocks, 'alt_url': alt_url}


def page_view(request, slug=None):
    '''Render a page template with a content
    '''
    template_name, data = get_page_data(request, slug)
    context = template.RequestContext(request)
    return shortcuts.render_to_response(template_name, data,
                                        context_instance=context)

'''Mixins useds for pages models.
'''
from django.conf import settings
from django.db import models
from django.utils.translation import get_language_info, ugettext_lazy as _


class ActivityMixin(models.Model):
    '''Mixin contains active field
    '''
    is_active = models.BooleanField(verbose_name=_('is active'), default=True)

    class Meta:
        abstract = True


class HTMLMetaMixin(models.Model):
    '''Mixin contains fields can be used to generate html meta tags and some
    other html > head tags

        title_tag - <title> tag
        meta_description - <meta name="description" content="..." />
        meta_keywords - <meta name="keywords" content="..." />
    '''
    title_tag = models.CharField(max_length=255, verbose_name=_('title'),
                                 blank=True, help_text=_('the title tag'))
    meta_description = models.TextField(verbose_name=_('description'),
                             blank=True, help_text=_('tag meta description'))
    meta_keywords = models.TextField(verbose_name=_('keywords'), blank=True,
                                     help_text=_('tag meta keywords'))

    class Meta:
        abstract = True


class Language(models.Model):
    '''Model represents language
    '''
    code = models.CharField(_('language code'), max_length=5, primary_key=True,
                            choices=settings.LANGUAGES)

    class Meta:
        verbose_name = _('language')
        verbose_name_plural = _('languages')

    def __str__(self):
        '''Get language name for it's code
        '''
        return self.name

    def __unicode__(self):
        '''Get language name for it's code
        '''
        return self.name

    def __repr__(self):
        '''Represent
        '''
        return ''.join(('<', self.__class__.__name__, ': "', self.code, '">'))

    def __eq__(self, other):
        '''Override checking for equels - the same objects has the same code
        '''
        return self.code == other.code

    @property
    def info(self):
        return get_language_info(self.code)

    @property
    def name(self):
        return self.info['name']

    @property
    def raw_code(self):
        return self.code


class NavigationMixin(models.Model):
    '''Mixin contains data for navigation generation

        alias - unique object identifier for current language
        header - content for h1 tag reprenenting the page and menu <a> tag text
        title - menu tag <a> title attribute
    '''
    alias = models.SlugField(verbose_name=_('alias'), unique=True,
                             help_text=_('URL string alias (slug)'))
    header = models.CharField(max_length=255, verbose_name=_('header'),
                              blank=True, help_text=_('H1 page tag'))
    title = models.CharField(max_length=255, verbose_name=_('title attr'),
                             blank=True, help_text=_('the title tag attr'))

    class Meta:
        abstract = True


class TranslatedMixin(models.Model):
    '''Mixin adds method to select object translation for specified language
    from translations field (required to be set). Can be used to make objects
    translated to different languages.

    As example for classes:

        class Article(models.Model, TranslatedMixin):
            name = models.CharField(max_length=255)

        class ArticleTranslation(TranslationMixin, models.Model):
            title = models.CharField(max_length=255)
            content = models.TextField()
            article = models.ForeignKey(Article, related_name='translations')

    We can get translation:

        article = Artcile.objects.get(name='Hello, world!')
        translation = article.get_translation('en')
    '''

    class Meta:
        abstract = True

    def get_translation(self, language=None):
        if not language:
            language = settings.LANGUAGE_CODE
        if isinstance(language, basestring):
            return self.translations.get(language_id=language)
        elif isinstance(language, Language):
            return self.translations.get(language=language)
        raise TypeError('%s.get_translation() accepts only string or Language '
                        'argument but %s given' % (self.__class__.__name__,
                                                   type(language)))


class TranslationMixin(models.Model):
    '''Mixin contains field related to language.
    '''
    language = models.ForeignKey(Language, verbose_name=_('language'))

    class Meta:
        abstract = True

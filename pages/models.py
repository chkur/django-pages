'''
Models for pages application:
-----------------------------

Page
Layout
Placeholder
PageTranslation
PageContent
PageArticle
'''
from django.db import models
from django.utils.translation import ugettext_lazy as _

import managers
import mixins

Language = mixins.Language


class Page(mixins.TranslatedMixin):
    '''Page object used to represent object's position inside a site objects
    hierarhy, activity state and can contains translation
    '''
    is_default = models.BooleanField(_('is default page'), default=False, db_index=True)

    class Meta:
        verbose_name = _('page')
        verbose_name_plural = _('pages')

    def __str__(self):
        '''Get string representation based on current locale: get translation
        title.
        '''

        str_value = 'Page object'
        try:
            str_value = self.get_translation().__str__()
        except PageTranslation.DoesNotExist:
            pass
        return str_value

    def __unicode__(self):
        '''Get unicode of current locale translation's title for this page
        '''
        return unicode(self.__str__())

    def save(self, *args, **kwargs):
        '''Save layout
        Because it can be only one layout selected update all other layouts to
        set their is_default values to False if current layout's is_default
        was set to True
        '''
        if self.is_default:
            query = self.__class__.objects.all()
            if self.pk:
                query = query.exclude(pk=self.pk)
            query = query.update(is_default=False)
        return super(Page, self).save(*args, **kwargs)


class Layout(mixins.ActivityMixin):
    '''Layout for building pages
    '''
    name = models.CharField(_('layout name'), max_length=128)
    template = models.CharField(_('layout template'), max_length=256)
    is_default = models.BooleanField(_('is default layout for page'),
                                     default=False)

    objects = managers.LayoutManager()

    class Meta:
        verbose_name = _('page layout')
        verbose_name_plural = _('page layouts')

    def save(self, *args, **kwargs):
        '''Save layout
        Because it can be only one layout selected update all other layouts to
        set their is_default values to False if current layout's is_default
        was set to True
        '''
        if self.is_default:
            query = self.__class__.objects.all()
            if self.pk:
                query = query.exclude(pk=self.pk)
            query = query.update(is_default=False)
        return super(Layout, self).save(*args, **kwargs)

    def __str__(self):
        '''Get string representation
        '''
        return self.name

    def __unicode__(self):
        '''Get unicode representation
        '''
        return unicode(self.name)


class Placeholder(models.Model):
    '''Placeholder in template
    '''
    alias = models.CharField(_('access name'), max_length=64, primary_key=True,
                             help_text=_('name for accessing from templates'))
    name = models.CharField(_('verbose name'), max_length=256,
                            help_text=_('name shown in admin interface'))

    def save(self, *args, **kwargs):
        '''Save placeholder into database
        If there is no name set take it from alias
        '''
        if not self.name:
            self.name = self.alias
        return super(Placeholder, self).save(*args, **kwargs)

    def __str__(self):
        '''Get placeholder name
        '''
        return self.name

    def __unicode__(self):
        '''Get name in unicode form
        '''
        return unicode(self.__str__())


class PageTranslation(mixins.ActivityMixin, mixins.HTMLMetaMixin,
                      mixins.NavigationMixin, mixins.TranslationMixin,
                      mixins.AltURLMixin):
    '''Represent page translation for current language
    '''
    page = models.ForeignKey(Page, related_name='translations',
                             verbose_name=_('page'))
    layout = models.ForeignKey(Layout, related_name='pages')

    class Meta:
        verbose_name = _('page translation')
        verbose_name_plural = _('pages translations')

    def save(self, *args, **kwargs):
        '''Save PageTranslation
        If there is no layout specified use default layout
        '''
        return super(PageTranslation, self).save(*args, **kwargs)

    def __str__(self):
        '''Get string representation
        '''
        return self.title_tag or self.header or self.title

    def __unicode__(self):
        '''Get unicode representation
        '''
        return unicode(self.__str__())


class PageContent(models.Model):
    '''Base class represents page content for language. It's just a base class
    for all page content classes
    '''
    page = models.ForeignKey(PageTranslation, related_name='content')
    layout = models.ForeignKey(Layout, related_name='blocks')
    place = models.ForeignKey(Placeholder, related_name='blocks')

    class Meta:
        abstract = True


class PageArticle(PageContent):
    '''Page contains an article
    '''
    article_title = models.CharField(_('article title'), max_length=1024,
                                     null=False, blank=False)
    text = models.TextField(_('page text'), help_text=_('page html content'),
                            null=False, blank=False)

    class Meta:
        verbose_name = _('page article')
        verbose_name_plural = _('page articles')

    def __str__(self):
        '''Get placeholder name
        '''
        return self.article_title

    def __unicode__(self):
        '''Get name in unicode form
        '''
        return unicode(self.__str__())


class MenuItem(models.Model):
    '''Item position
    '''
    menu = models.ForeignKey('Menu', verbose_name=_('menu'))
    page = models.ForeignKey(Page, verbose_name=_('page'))
    order = models.IntegerField(_('consecutive number'))

    class Meta:
        verbose_name = _('menu item')
        verbose_name_plural = _('menu items')
        ordering = ('order', )

    # def __str__(self):
    #     '''Get placeholder name
    #     '''
    #     return str(self.menu) + ': ' + str(self.page)

    def __unicode__(self):
        '''Get name in unicode form
        '''
        return '%s: %s' % (self.menu, self.page)


class Menu(mixins.ActivityMixin):
    '''Add a menus
    '''
    name = models.CharField(_('menu name'), max_length=255)
    alias = models.CharField(_('template alias'), max_length=64,
                             primary_key=True)
    items = models.ManyToManyField(Page, through=MenuItem,
                                   verbose_name=_('pages'))

    class Meta:
        verbose_name = _('menu')
        verbose_name_plural = _('menus')

    def __str__(self):
        '''Get placeholder name
        '''
        return self.name

    def __unicode__(self):
        '''Get name in unicode form
        '''
        return unicode(self.__str__())

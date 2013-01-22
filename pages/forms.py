'''Forms for pages
'''
import re

import unidecode

from django import forms
from django.contrib.admin import widgets
from django.utils.translation import ugettext_lazy as _

from tinymce.widgets import TinyMCE

import models


def slugify(text):
    '''Get a slug of a text
    '''
    text = unidecode.unidecode(text).lower()
    return re.sub(r'\W+', '-', text)


class PageTranslationForm(forms.ModelForm):
    '''Form for translations
    '''

    def __init__(self, *args, **kwargs):
        '''Create PageTranslationForm.

        Request language attribute and also accepts optional object attribute.
        They would be used on object saving
        '''
        # Get language and page
        self.language = kwargs['language']
        del kwargs['language']
        kwargs['prefix'] = self.language.raw_code
        if 'page' in kwargs:
            self.page = kwargs['page']
            del kwargs['page']
        else:
            self.page = None
        # Create form
        super(PageTranslationForm, self).__init__(*args, **kwargs)
        self.fields['title_tag'].required = True  # Requred
        self.fields['layout'].widget.attrs['class'] = 'layout-choose'

    def clean(self):
        '''Set default values
        '''
        cleaned_data = super(PageTranslationForm, self).clean()
        if not cleaned_data.get('title', None):
            cleaned_data['title'] = cleaned_data.get('title_tag', '')
        if not cleaned_data.get('header', None):
            cleaned_data['header'] = cleaned_data.get('title_tag', '')
        if not cleaned_data.get('alias', None):
            cleaned_data['alias'] = slugify(cleaned_data.get('title_tag', ''))
        return cleaned_data

    def save(self, commit=True, page=None):
        '''Save object
        '''
        # Not commits yet
        translation = super(PageTranslationForm, self).save(commit=False)
        # Update translation with language and page
        translation.language = self.language
        translation.page = page or self.page
        if commit:  # Commit changes if needed
            translation.save()
        return translation

    FIELD_GROUPS = (
        ('title_tag', 'layout', 'alias', 'alt_url'),
        ('header', 'title', 'is_active', ),
        ('meta_description', 'meta_keywords', )
    )

    def fieldsets(self):
        '''Group fields into fieldsets
        '''
        fieldsets = {}
        for field in self:
            index = 0
            for group in PageTranslationForm.FIELD_GROUPS:
                index += 1
                if field.name in group:
                    if index in fieldsets:
                        fieldsets[index].append(field)
                    else:
                        fieldsets[index] = [field]
        return [fieldsets[index] for index in fieldsets]

    @property
    def layout(self):
        '''Get instance layout
        '''
        if hasattr(self, 'cleaned_data') and self.cleaned_data['layout']:
            return self.cleaned_data['layout']
        elif self.instance and self.instance.layout_id:
            return self.instance.layout
        return None

    class Meta:
        model = models.PageTranslation
        exclude = ('language', 'page', )  # Set them manually


class PageContentForm(forms.ModelForm):
    '''Form for page content
    '''

    def __init__(self, *args, **kwargs):
        '''Build new forms includes
        '''
        # Get arguments
        self.layout = kwargs['layout']
        del kwargs['layout']
        self.place = kwargs['place']
        del kwargs['place']
        if 'page' in kwargs:
            self.page = kwargs['page']
            del kwargs['page']
        else:
            self.page = None
        kwargs['prefix'] = '-'.join([kwargs['language'].raw_code,
                                     str(self.layout.pk), str(self.place.pk)])
        del kwargs['language']
        kwargs['initial'] = kwargs.get('initial', {'is_active': True})
        # Create form
        super(PageContentForm, self).__init__(*args, **kwargs)
        # Update a widget
        self.fields['text'].widget = TinyMCE()

    def save(self, commit=True, page=None):
        '''Save object
        '''
        # Not commits yet
        content = super(PageContentForm, self).save(commit=False)
        # Update content block with language and page
        content.layout = self.layout
        content.page = page or self.page
        content.place = self.place
        if commit:  # Commit changes if needed
            content.save()
        return content

    class Meta:
        model = models.PageArticle
        exclude = ('layout', 'page', 'place', )  # Set them manually


def get_filter_func(items):
    '''Get function for 
    '''
    def filter_func(item):
        return item.id in items
    return filter_func


def get_cmp_func(order):
    '''Get comparision function
    '''
    def cmp_func(first, second):
        return order.index(int(first.id)) > order.index(int(second.id))
    return cmp_func


class MenuForm(forms.ModelForm):
    '''Manage menus
    '''
    items = forms.ModelMultipleChoiceField(
                        queryset=models.Page.objects.all(), required=False,
                        widget=widgets.FilteredSelectMultiple(is_stacked=False,
                                                verbose_name=_('menu items')))

    class Meta:
        model = models.Menu

    def __init__(self, *args, **kwargs):
        '''Create new form and get initial data from items
        '''
        super(MenuForm, self).__init__(*args, **kwargs)
        if self.instance:
            items = models.MenuItem.objects.filter(menu=self.instance)
            if len(self.data) > 0:
                order = [int(item_id)
                         for item_id in self.data.getlist('items')]
                ordered_items = sorted(filter(get_filter_func(order), items),
                                       cmp=get_cmp_func(order))
            else:
                ordered_items = items.order_by('order')
            self.fields['items'].initial = ordered_items

    def save(self, commit=True):
        '''Save menu with items in order
        '''
        menu = super(MenuForm, self).save(commit=False)
        menu.items.clear()
        if commit:
            menu.save()
        items = self.cleaned_data['items']
        order = {int(id): index
                 for index, id in enumerate(self.data.getlist('items'))}
        for item in items:
            models.MenuItem.objects.create(menu=menu, page=item,
                                           order=order[item.id])
        return menu

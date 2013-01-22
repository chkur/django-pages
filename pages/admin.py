'''Build an admin interface for pages and page-related things
'''
import functools
import urlparse

from django import http
from django.conf import settings
from django.conf.urls import defaults as urls
from django.contrib import admin
from django.core import exceptions, urlresolvers
from django.db import transaction
from django.views.decorators import csrf
from django.utils import decorators, encoding, functional, html, safestring
from django.utils.translation import ugettext as _

import forms
import models

csrf_protect_m = decorators.method_decorator(csrf.csrf_protect)


def back_redirect(request):
    '''Generate response to redirect ro previous page
    '''
    if 'HTTP_REFERER' in request.META:
        url = urlparse.urljoin(request.META['HTTP_REFERER'],
                               request.META['QUERY_STRING'])
    else:
        url = '/admin/'
    return http.HttpResponseRedirect(url)


class ActivityMixin(admin.ModelAdmin):
    '''Mixin
    '''
    def do_change_active(obj):
        '''Change delete status
        '''
        is_active = obj.is_active
        icon = is_active and 'icon-yes.gif' or 'icon-no.gif'
        action = is_active and 'deactivate' or 'activate'
        msg = is_active and 'Restore file' or 'Delete file'
        return safestring.mark_safe('''
            <a class='active_switch' title='%s' href="%s/%s/">
                <img alt="%s" src="%s/admin/img/%s" />
            </a>''' % (msg, obj.pk, action, msg, settings.STATIC_URL, icon))
    do_change_active.allow_tags = True
    do_change_active.short_description = _('is active')
    do_change_active = staticmethod(do_change_active)

    def change_active(self, request, object_id, is_active):
        '''Change document deleted state
        '''
        obj = self.get_object(request, object_id)
        if obj.is_active != is_active:
            obj.is_active = is_active
            obj.save()
        return back_redirect(request)

    def get_urls(self):
        """Get urls for make object active/inactive
        """
        def wrap(view):
            '''Wrap object with permissions checking
            '''
            def wrapper(*args, **kwargs):
                '''View wrapper
                '''
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return functools.update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name
        urlpatterns = urls.patterns('',
            urls.url(r'^(.+)/activate/$', wrap(self.change_active),
                     {'is_active': True}, name='%s_%s_change' % info, ),
            urls.url(r'^(.+)/deactivate/$', wrap(self.change_active),
                     {'is_active': False}, name='%s_%s_change' % info, ),
        )
        return urlpatterns + super(ActivityMixin, self).get_urls()


class LanguageAdmin(admin.ModelAdmin):
    '''Class represents admin interface for language model
    '''
    model = models.Language
    list_display = ('name', 'raw_code', )

admin.site.register(models.Language, LanguageAdmin)


class LayoutAdmin(admin.ModelAdmin):
    '''Admin iterface for layouts list
    '''
    model = models.Layout
    list_display = ('name', 'template', 'is_default', 'is_active', )
    fields = ('name', 'template', 'is_default', 'is_active', )

admin.site.register(models.Layout, LayoutAdmin)


class PageAdmin(admin.ModelAdmin):
    '''Class represents admin interface for page model
    '''
    model = models.Page
    add_form_template = 'admin/page_change_form.html'
    change_form_template = 'admin/page_change_form.html'
    search_fields = ('translations__header', 'translations__title',
                     'translations__alias', )
    list_filter = ('translations__layout', )
    list_display = ('title', 'alias', 'layout')

    def title(self, obj):
        '''Get title
        '''
        return unicode(obj)
    title.short_description = _('title')

    def alias(self, obj):
        '''Get alias
        '''
        return obj.get_translation().alias
    alias.short_description = _('alias')

    def layout(self, obj):
        '''Get layout
        '''
        return obj.get_translation().layout
    layout.short_description = _('layout')

    def get_urls(self):
        '''Get urls accessible in admin interface
        '''
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            return functools.update_wrapper(wrapper, view)

        info = self.model._meta.app_label, self.model._meta.module_name

        return urls.patterns('',
            urls.url('^get_layout_form/(?P<page_id>\w+)/(?P<layout_id>\w+)/' +
                     '(?P<lang_code>\w+)$',
                     wrap(self.layout_view),
                     name='%s_%s_get_layout_form' % info),
            urls.url('^get_layout_form/(?P<layout_id>\w+)/(?P<lang_code>\w+)$',
                     wrap(self.layout_view),
                     name='%s_%s_get_layout_form' % info),
        ) + super(PageAdmin, self).get_urls()


    def get_placeholders(self, template_name):
        '''Get a list of placeholders for layout
        '''
        aliases = settings.PAGES_TEMPLATES_PLACEHOLDERS.get(template_name, ())
        return [models.Placeholder.objects.get_or_create(alias=alias)[0]
                for alias in aliases]

    def render_layout_form(self, language, layout, page):
        '''
        '''
        from django.template import loader
        if page:
            def get_instance(place):
                return models.PageArticle.objects.get_or_create(layout=layout,
                                                    page=page, place=place)[0]
        else:
            get_instance = lambda __: None

        formset = [forms.PageContentForm(None, layout=layout, place=place,
                                         instance=get_instance(place),
                                         language=language)
                   for place in self.get_placeholders(layout.template)]
        return loader.render_to_string('admin/includes/content_form.html',
                                       {'formset': formset})

    @csrf_protect_m
    def layout_view(self, request, page_id=None, layout_id=None,
                    lang_code=None):
        '''Get a lyout
        '''
        # Select language
        lang_code = lang_code or settings.LANGUAGE_CODE
        lang = models.Language.objects.get(code=lang_code)
        # Select layout
        layout_manager = models.Layout.objects
        layout = (layout_manager.get(id=layout_id) if layout_id
                  else self.default_layout)
        # Select page
        if page_id:
            page = models.PageTranslation.objects.get(page_id=page_id,
                                                      language=lang)
        else:
            page = None

        return http.HttpResponse(self.render_layout_form(lang, layout, page))

    @functional.cached_property
    def default_layout(self):
        '''Get default layout
        '''
        return models.Layout.objects.get_default()

    def validate_forms(self, forms):
        '''Validate a list of forms
        '''
        return functools.reduce(lambda valid, form: form.is_valid() and valid,
                                forms, True)

    def validate_inlines(self, translations):
        '''Validate a list forms for contents
        '''
        return functools.reduce(
                lambda valid, transl:
                        self.validate_forms(transl.content_forms) and valid,
                translations, True)

    def get_translation_forms(self, data=None, page=None):
        '''Get a list of forms for different languages
        '''
        if page:
            get_instance = lambda lang: models.PageTranslation.objects.get(
                                                    page=page, language=lang)
        else:
            get_instance = lambda __: None
        return [forms.PageTranslationForm(data, language=language,
                                instance=get_instance(language), page=page,
                                initial={'is_active': True,
                                         'layout__id': self.default_layout.id})
                for language in models.Language.objects.all()]

    def get_layout_forms(self, translations, data=None, page=None):
        '''Get layout forms
        '''
        if page:
            def get_instance(transl, place, layout):
                page_translation = models.PageTranslation.objects.get(
                                        page=page, language=transl.language)
                return models.PageArticle.objects.get_or_create(layout=layout,
                                        page=page_translation, place=place)[0]
        else:
            get_instance = lambda __, ___, ____: None
        for translation in translations:
            layout = translation.layout or self.default_layout
            translation.content_forms = [
                forms.PageContentForm(data, layout=layout, place=placeholder,
                    instance=get_instance(translation, placeholder, layout),
                    language=translation.language)
                for placeholder in self.get_placeholders(layout.template)]

    def save_data(self, request, new_object, form, translations):
        '''Save model and translations with whole data
        '''
        self.save_model(request, new_object, form, True)
        for translation in translations:
            tranls_obj = translation.save(page=new_object)
            for content in translation.content_forms:
                content.save(page=tranls_obj)

    @csrf_protect_m
    @transaction.commit_on_success
    def add_view(self, request, form_url='', extra_context=None):
        '''The 'add' admin view for this model.
        '''
        model = self.model
        opts = model._meta

        if not self.has_add_permission(request):
            raise exceptions.PermissionDenied

        ModelForm = self.get_form(request)
        if request.method == 'POST':
            # Trying to create new post
            form = ModelForm(request.POST, request.FILES)
            if form.is_valid():
                new_object = self.save_form(request, form, change=False)
                form_validated = True
            else:
                form_validated = False
                new_object = self.model()
            # Validate additional data
            translations = self.get_translation_forms(request.POST)
            transl_valid = self.validate_forms(translations)
            self.get_layout_forms(translations, request.POST)
            inlines_valid = self.validate_inlines(translations)
            # If data valid can save results
            if form_validated and transl_valid and inlines_valid:
                self.log_addition(request, new_object)
                self.save_data(request, new_object, form, translations)
                return self.response_add(request, new_object)
        else:
            # Prepare the dict of initial data from the request.
            initial = dict(request.GET.items())
            for k in initial:
                try:
                    field = opts.get_field(k)
                except models.FieldDoesNotExist:
                    continue
                if isinstance(field, models.ManyToManyField):
                    initial[k] = initial[k].split(",")
            form = ModelForm(initial=initial)
            # Prepare translations
            translations = self.get_translation_forms()
            self.get_layout_forms(translations)
        # Create an admin form
        adminForm = admin.helpers.AdminForm(form,
                                        list(self.get_fieldsets(request)),
                                        self.get_prepopulated_fields(request),
                                        self.get_readonly_fields(request),
                                        model_admin=self)
        media = self.media + adminForm.media

        context = {
            'title': _('Add %s') % encoding.force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'is_popup': "_popup" in request.REQUEST,
            'show_delete': False,
            'media': media,
            'errors': admin.helpers.AdminErrorList(form, []),
            'app_label': opts.app_label,
            'translations': translations
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, form_url=form_url,
                                       add=True)

    @csrf_protect_m
    @transaction.commit_on_success
    def change_view(self, request, object_id, form_url='', extra_context=None):
        "The 'change' admin view for this model."
        model = self.model
        opts = model._meta

        obj = self.get_object(request, admin.util.unquote(object_id))

        if not self.has_change_permission(request, obj):
            raise exceptions.PermissionDenied

        if obj is None:
            raise exceptions.Http404(
                _('%(name)s object with primary key %(key)r does not exist.') %
                           {'name': encoding.force_unicode(opts.verbose_name),
                            'key': html.escape(object_id)})

        if request.method == 'POST' and "_saveasnew" in request.POST:
            url = urlresolvers.reverse('admin:%s_%s_add' %
                                       (opts.app_label, opts.module_name),
                                       current_app=self.admin_site.name)
            return self.add_view(request, form_url=url)

        ModelForm = self.get_form(request, obj)
        if request.method == 'POST':
            # Validate save form
            form = ModelForm(request.POST, request.FILES, instance=obj)

            if form.is_valid():
                form_validated = True
                new_object = self.save_form(request, form, change=True)
            else:
                form_validated = False
                new_object = obj
            # Validate translations, conten
            translations = self.get_translation_forms(request.POST, obj)
            transl_valid = self.validate_forms(translations)
            self.get_layout_forms(translations, request.POST, obj)
            inlines_valid = self.validate_inlines(translations)
            # If all valid real save
            if form_validated and transl_valid and inlines_valid:
                self.save_data(request, new_object, form, translations)
                change_message = self.construct_change_message(request, form,
                                                               [])
                self.log_change(request, new_object, change_message)
                return self.response_change(request, new_object)
        else:
            # Create new form
            form = ModelForm(instance=obj)
            translations = self.get_translation_forms(page=obj)
            self.get_layout_forms(translations, None, obj)

        adminForm = admin.helpers.AdminForm(form,
                                    self.get_fieldsets(request, obj),
                                    self.get_prepopulated_fields(request, obj),
                                    self.get_readonly_fields(request, obj),
                                    model_admin=self)
        media = self.media + adminForm.media

        context = {
            'title': _('Change %s') %
                     encoding.force_unicode(opts.verbose_name),
            'adminform': adminForm,
            'object_id': object_id,
            'original': obj,
            'is_popup': "_popup" in request.REQUEST,
            'media': media,
            'errors': admin.helpers.AdminErrorList(form, []),
            'app_label': opts.app_label,
            'translations': translations
        }
        context.update(extra_context or {})
        return self.render_change_form(request, context, change=True, obj=obj,
                                       form_url=form_url)

admin.site.register(models.Page, PageAdmin)


class MenuAdmin(ActivityMixin):
    '''Admin interface for menus
    '''
    model = models.Menu
    form = forms.MenuForm
    list_display = ('name', 'alias', ActivityMixin.do_change_active, )

    def save_related(self, request, form, formsets, change):
        """Given the ``HttpRequest``, the parent ``ModelForm`` instance, the
        list of inline formsets and a boolean value based on whether the
        parent is being added or changed, save the related objects to the
        database. Note that at this point save_form() and save_model() have
        already been called.
        """
        for formset in formsets:
            self.save_formset(request, form, formset, change=change)

admin.site.register(models.Menu, MenuAdmin)
admin.site.register(models.MenuItem)

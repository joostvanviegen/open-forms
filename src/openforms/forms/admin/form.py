from django import forms
from django.contrib import admin, messages
from django.core.exceptions import PermissionDenied
from django.core.management import CommandError, call_command
from django.http.response import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.translation import ugettext_lazy as _

from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline
from reversion.admin import VersionAdmin

from openforms.registrations.admin import BackendChoiceFieldMixin

from ..backends import registry
from ..forms.form import FormImportForm
from ..models import Form, FormStep


class FormStepInline(OrderedTabularInline):
    model = FormStep
    fk_name = "form"
    fields = (
        "order",
        "move_up_down_links",
        "form_definition",
        "optional",
        "availability_strategy",
    )
    readonly_fields = (
        "order",
        "move_up_down_links",
    )
    ordering = ("order",)
    extra = 1


@admin.register(Form)
class FormAdmin(BackendChoiceFieldMixin, OrderedInlineModelAdminMixin, VersionAdmin):
    list_display = ("name", "active", "registration_backend", "registration_backend_options")
    inlines = (FormStepInline,)
    prepopulated_fields = {"slug": ("name",)}

    change_list_template = (
        "admin/forms/form/change_list.html"  # override reversion template
    )

    def _reversion_autoregister(self, model, follow):
        # because this is called in the __init__, it seems to run before the
        # `AppConfig.ready` hook runs, causing regisgration errors.
        pass

    def response_post_save_change(self, request, obj):
        if "_copy" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            copied_form = obj.copy()

            messages.success(
                request,
                _("{} {} was successfully copied").format("Form", obj),
            )
            return HttpResponseRedirect(
                reverse("admin:forms_form_change", args=(copied_form.pk,))
            )
        if "_export" in request.POST:
            # Clear messages
            storage = messages.get_messages(request)
            for i in storage:
                pass

            response = HttpResponse(content_type="application/zip")
            response["Content-Disposition"] = f"attachment;filename={obj.slug}.zip"
            call_command("export", obj.pk, response=response)

            response["Content-Length"] = len(response.content)

            self.message_user(
                request,
                _("{} {} was successfully exported").format("Form", obj),
                level=messages.SUCCESS,
            )
            return response
        else:
            return super().response_post_save_change(request, obj)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_view),
                name="forms_import",
            )
        ]
        return my_urls + urls

    def import_view(self, request):
        if not self.has_add_permission(request):
            raise PermissionDenied

        if "_import" in request.POST:
            form = FormImportForm(request.POST, request.FILES)
            if form.is_valid():
                try:
                    import_file = form.cleaned_data["file"]
                    call_command("import", import_file=import_file)
                    self.message_user(
                        request,
                        _("Catalogus successfully imported"),
                        level=messages.SUCCESS,
                    )
                    return HttpResponseRedirect(reverse("admin:forms_form_changelist"))
                except CommandError as exc:
                    self.message_user(request, exc, level=messages.ERROR)
        else:
            form = FormImportForm()

        context = dict(self.admin_site.each_context(request), form=form)

        return TemplateResponse(request, "admin/forms/form/import_form.html", context)

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "backend":
            choices = [(path, path.split(".")[-1]) for path in registry]
            choices.insert(0, ("", "---------"))

            return forms.ChoiceField(
                label=db_field.verbose_name.capitalize(),
                choices=choices,
                required=False,
                help_text=db_field.help_text,
            )

        return super().formfield_for_dbfield(db_field, request, **kwargs)

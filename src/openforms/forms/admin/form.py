from django.contrib import admin, messages
from django.http.response import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils.html import format_html_join
from django.utils.translation import ngettext, ugettext_lazy as _

from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from openforms.config.models import GlobalConfiguration
from openforms.payments.admin import PaymentBackendChoiceFieldMixin
from openforms.registrations.admin import RegistrationBackendFieldMixin
from openforms.utils.expressions import FirstNotBlank

from ..models import Form, FormDefinition, FormStep
from ..models.form import FormsExport
from ..utils import export_form, get_duplicates_keys_for_form
from .mixins import FormioConfigMixin
from .views import (
    DownloadExportedFormsView,
    ExportFormsForm,
    ExportFormsView,
    ImportFormsView,
)


class FormStepInline(OrderedTabularInline):
    model = FormStep
    fk_name = "form"
    fields = (
        "order",
        "move_up_down_links",
        "form_definition",
        "optional",
        "previous_text",
        "save_text",
        "next_text",
    )
    readonly_fields = (
        "order",
        "move_up_down_links",
    )
    ordering = ("order",)
    extra = 1


class FormDeletedListFilter(admin.ListFilter):
    title = _("is deleted")
    parameter_name = "deleted"

    def __init__(self, request, params, model, model_admin):
        super().__init__(request, params, model, model_admin)

        self.request = request

        if self.parameter_name in params:
            value = params.pop(self.parameter_name)
            self.used_parameters[self.parameter_name] = value

    def show_deleted(self):
        return self.used_parameters.get(self.parameter_name) == "deleted"

    def has_output(self):
        """
        This needs to return ``True`` to work.
        """
        return True

    def choices(self, changelist):
        result = [
            {
                "selected": not self.show_deleted(),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: "available"}
                ),
                "display": _("Available forms"),
            },
            {
                "selected": self.show_deleted(),
                "query_string": changelist.get_query_string(
                    {self.parameter_name: "deleted"}
                ),
                "display": _("Deleted forms"),
            },
        ]
        return result

    def queryset(self, request, queryset):
        if self.show_deleted():
            return queryset.filter(_is_deleted=True)
        else:
            return queryset.filter(_is_deleted=False)

    def expected_parameters(self):
        return [self.parameter_name]


@admin.register(Form)
class FormAdmin(
    FormioConfigMixin,
    RegistrationBackendFieldMixin,
    PaymentBackendChoiceFieldMixin,
    OrderedInlineModelAdminMixin,
    admin.ModelAdmin,
):
    list_display = (
        "anno_name",
        "active",
        "maintenance_mode",
        "get_authentication_backends_display",
        "get_payment_backend_display",
        "get_registration_backend_display",
        "get_object_actions",
    )
    prepopulated_fields = {"slug": ("name",)}
    actions = [
        "make_copies",
        "set_to_maintenance_mode",
        "remove_from_maintenance_mode",
        "export_forms",
    ]
    list_filter = ("active", "maintenance_mode", FormDeletedListFilter)
    search_fields = ("name", "internal_name")

    change_list_template = "admin/forms/form/change_list.html"

    def changelist_view(self, request, extra_context=None):
        context = {
            "has_change_permission": self.has_change_permission(request),
        }
        context.update(extra_context or {})
        return super().changelist_view(request, context)

    def get_queryset(self, request):
        # annotate .name for ordering
        return (
            super()
            .get_queryset(request)
            .annotate(anno_name=FirstNotBlank("internal_name", "name"))
        )

    def get_object_actions(self, obj) -> str:
        links = ((obj.get_absolute_url(), _("Show form")),)
        return format_html_join(" | ", '<a href="{}" target="_blank">{}</a>', links)

    get_object_actions.short_description = _("Actions")

    def anno_name(self, obj):
        return obj.admin_name

    anno_name.admin_order_field = "anno_name"
    anno_name.short_description = _("name")

    def get_form(self, request, *args, **kwargs):
        if kwargs.get("change"):
            # Display a warning if duplicate keys are used in form definitions
            duplicate_keys = get_duplicates_keys_for_form(args[0])

            if duplicate_keys:
                error_message = _("{} occurs in both {}")
                error_messages = "; ".join(
                    [
                        error_message.format(key, ", ".join(form_definitions))
                        for key, form_definitions in duplicate_keys.items()
                    ]
                )
                self.message_user(
                    request,
                    _(
                        "The following form definitions contain fields with duplicate keys: %s"
                    )
                    % (error_messages),
                    level=messages.WARNING,
                )

        # no actual changes to the fields are triggered, we're only ending up here
        # because of the copy/export actions.
        kwargs["fields"] = ()
        return super().get_form(request, *args, **kwargs)

    def get_prepopulated_fields(self, request, obj=None):
        return {}

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
            export_form(obj.pk, response=response)

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
                self.admin_site.admin_view(ImportFormsView.as_view()),
                name="forms_import",
            ),
            path(
                "export/",
                self.admin_site.admin_view(ExportFormsView.as_view()),
                name="forms_export",
            ),
        ]
        return my_urls + urls

    def make_copies(self, request, queryset):
        for instance in queryset:
            instance.copy()

        messages.success(
            request,
            ngettext(
                "Copied {count} {verbose_name}",
                "Copied {count} {verbose_name_plural}",
                len(queryset),
            ).format(
                count=len(queryset),
                verbose_name=queryset.model._meta.verbose_name,
                verbose_name_plural=queryset.model._meta.verbose_name_plural,
            ),
        )

    make_copies.short_description = _("Copy selected %(verbose_name_plural)s")

    def set_to_maintenance_mode(self, request, queryset):
        count = queryset.filter(maintenance_mode=False).update(maintenance_mode=True)
        messages.success(
            request,
            ngettext(
                "Set {count} {verbose_name} to maintenance mode",
                "Set {count} {verbose_name_plural} to maintenance mode",
                count,
            ).format(
                count=count,
                verbose_name=queryset.model._meta.verbose_name,
                verbose_name_plural=queryset.model._meta.verbose_name_plural,
            ),
        )

    set_to_maintenance_mode.short_description = _(
        "Set selected %(verbose_name_plural)s to maintenance mode"
    )

    def remove_from_maintenance_mode(self, request, queryset):
        count = queryset.filter(maintenance_mode=True).update(maintenance_mode=False)
        messages.success(
            request,
            ngettext(
                "Removed {count} {verbose_name} from maintenance mode",
                "Removed {count} {verbose_name_plural} from maintenance mode",
                count,
            ).format(
                count=count,
                verbose_name=queryset.model._meta.verbose_name,
                verbose_name_plural=queryset.model._meta.verbose_name_plural,
            ),
        )

    remove_from_maintenance_mode.short_description = _(
        "Remove %(verbose_name_plural)s from maintenance mode"
    )

    def delete_model(self, request, form):
        """
        Check if we need to soft or hard delete.
        """
        if not form._is_deleted:
            # override for soft-delete
            form._is_deleted = True
            form.save(update_fields=["_is_deleted"])
        else:
            fds = list(
                FormDefinition.objects.filter(
                    formstep__form=form, is_reusable=False
                ).values_list("id", flat=True)
            )
            form.delete()
            FormDefinition.objects.filter(id__in=fds).delete()

    def delete_queryset(self, request, queryset):
        """
        Split between soft and hard deletes here.

        The admin has mutually exclusive filters, but let's not rely on that assumption.
        Hard deletes need to be performed first, otherwise non-deleted forms get
        soft-deleted and in the next steps _all_ (including the just created) soft-
        deletes get hard-deleted.
        """
        # hard deletes - ensure we cascade delete the single-use form definitions as well
        soft_deleted = queryset.filter(_is_deleted=True)
        fds = list(
            FormDefinition.objects.filter(
                formstep__form__in=soft_deleted, is_reusable=False
            ).values_list("id", flat=True)
        )
        soft_deleted.delete()
        FormDefinition.objects.filter(id__in=fds).delete()

        # soft-deletes
        queryset.filter(_is_deleted=False).update(_is_deleted=True)

    @admin.action(description=_("Export forms"))
    def export_forms(self, request, queryset):
        if not request.user.email:
            self.message_user(
                request=request,
                message=_(
                    "Please configure your email address in your admin profile before requesting a bulk export"
                ),
                level=messages.ERROR,
            )
            return

        selected_forms_uuids = queryset.values_list("uuid", flat=True)
        form = ExportFormsForm(
            initial={
                "forms_uuids": [str(form_uuid) for form_uuid in selected_forms_uuids],
            }
        )
        context = dict(self.admin_site.each_context(request), form=form)
        return TemplateResponse(request, "admin/forms/form/export.html", context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        config = GlobalConfiguration.get_solo()
        extra_context["feature_flags"] = {
            "enable_form_variables": config.enable_form_variables
        }
        return super().change_view(
            request,
            object_id,
            form_url,
            extra_context=extra_context,
        )


@admin.register(FormsExport)
class FormsExportAdmin(admin.ModelAdmin):
    list_display = ("uuid", "user", "datetime_requested")
    list_filter = ("user",)
    search_fields = ("user__username",)

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path(
                "download/<uuid:uuid>/",
                self.admin_site.admin_view(DownloadExportedFormsView.as_view()),
                name="download_forms_export",
            ),
        ]
        return my_urls + urls

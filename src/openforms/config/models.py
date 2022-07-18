from collections import defaultdict

from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.template import Context, Template
from django.template.loader import render_to_string
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from colorfield.fields import ColorField
from django_better_admin_arrayfield.models.fields import ArrayField
from glom import glom
from solo.models import SingletonModel
from tinymce.models import HTMLField

from openforms.config.constants import CSPDirective
from openforms.data_removal.constants import RemovalMethods
from openforms.emails.validators import URLSanitationValidator
from openforms.payments.validators import validate_payment_order_id_prefix
from openforms.utils.fields import SVGOrImageField
from openforms.utils.translations import ensure_default_language, runtime_gettext
from openforms.utils.validators import DjangoTemplateValidator


@ensure_default_language()
def get_confirmation_email_subject():
    return render_to_string("emails/confirmation_email/subject.txt").strip()


@ensure_default_language()
def get_confirmation_email_content():
    return render_to_string("emails/confirmation_email/content.html")


class GlobalConfiguration(SingletonModel):
    email_template_netloc_allowlist = ArrayField(
        models.CharField(max_length=1000),
        verbose_name=_("allowed email domain names"),
        help_text=_(
            "Provide a list of allowed domains (without 'https://www')."
            "Hyperlinks in a (confirmation) email are removed, unless the "
            "domain is provided here."
        ),
        blank=True,
        default=list,
    )

    submission_confirmation_template = HTMLField(
        _("submission confirmation template"),
        help_text=_(
            "The content of the submission confirmation page. It can contain variables that will be "
            "templated from the submitted form data."
        ),
        default=runtime_gettext(_("Thank you for submitting this form.")),
        validators=[DjangoTemplateValidator()],
    )

    confirmation_email_subject = models.CharField(
        _("subject"),
        max_length=1000,
        help_text=_(
            "Subject of the confirmation email message. Can be overridden on the form level"
        ),
        default=get_confirmation_email_subject,
        validators=[DjangoTemplateValidator()],
    )

    confirmation_email_content = HTMLField(
        _("content"),
        help_text=_(
            "Content of the confirmation email message. Can be overridden on the form level"
        ),
        default=get_confirmation_email_content,
        validators=[
            DjangoTemplateValidator(
                required_template_tags=[
                    "appointment_information",
                    "payment_information",
                ]
            ),
            URLSanitationValidator(),
        ],
    )

    allow_empty_initiator = models.BooleanField(
        _("allow empty initiator"),
        default=False,
        help_text=_(
            "When enabled and the submitter is not authenticated, a case is "
            "created without any initiator. Otherwise, a fake initiator is "
            "added with BSN 111222333."
        ),
    )

    form_previous_text = models.CharField(
        _("previous text"),
        max_length=50,
        default=runtime_gettext(_("Previous page")),
        help_text=_(
            "The text that will be displayed in the overview page to "
            "go to the previous step"
        ),
    )
    form_change_text = models.CharField(
        _("change text"),
        max_length=50,
        default=runtime_gettext(_("Change")),
        help_text=_(
            "The text that will be displayed in the overview page to "
            "change a certain step"
        ),
    )
    form_confirm_text = models.CharField(
        _("confirm text"),
        max_length=50,
        default=runtime_gettext(_("Confirm")),
        help_text=_(
            "The text that will be displayed in the overview page to "
            "confirm the form is filled in correctly"
        ),
    )
    form_begin_text = models.CharField(
        _("begin text"),
        max_length=50,
        default=runtime_gettext(_("Begin form")),
        help_text=_(
            "The text that will be displayed at the start of the form to "
            "indicate the user can begin to fill in the form"
        ),
    )

    form_step_previous_text = models.CharField(
        _("step previous text"),
        max_length=50,
        default=runtime_gettext(_("Previous page")),
        help_text=_(
            "The text that will be displayed in the form step to go to the previous step"
        ),
    )
    form_step_save_text = models.CharField(
        _("step save text"),
        max_length=50,
        default=runtime_gettext(_("Save current information")),
        help_text=_(
            "The text that will be displayed in the form step to save the current information"
        ),
    )
    form_step_next_text = models.CharField(
        _("step next text"),
        max_length=50,
        default=runtime_gettext(_("Next")),
        help_text=_(
            "The text that will be displayed in the form step to go to the next step"
        ),
    )
    form_fields_required_default = models.BooleanField(
        verbose_name=_("Mark form fields 'required' by default"),
        default=False,
        help_text=_(
            "Whether the checkbox 'required' on form fields should be checked by default."
        ),
    )
    form_display_required_with_asterisk = models.BooleanField(
        verbose_name=_("Mark required fields with asterisks"),
        default=True,
        help_text=_(
            "If checked, required fields are marked with an asterisk and optional "
            "fields are unmarked. If unchecked, optional fields will be marked with "
            "'(optional)' and required fields are unmarked."
        ),
    )

    # 'subdomain' styling & content configuration
    # FIXME: do not expose this field via the API to non-admin users! There is not
    # sufficient input validation to protect against the SVG attack surface. The SVG
    # is rendered by the browser of end-users.
    #
    # See https://www.fortinet.com/blog/threat-research/scalable-vector-graphics-attack-surface-anatomy
    #
    # * XSS
    # * HTML Injection
    # * XML entity processing
    # * DoS
    logo = SVGOrImageField(
        _("municipality logo"),
        upload_to="logo/",
        blank=True,
        help_text=_(
            "Upload the municipality logo, visible to users filling out forms. We "
            "advise dimensions around 150px by 75px. SVG's are allowed."
        ),
    )
    main_website = models.URLField(
        _("main website link"),
        blank=True,
        help_text=_(
            "URL to the main website. Used for the 'back to municipality website' link."
        ),
    )
    # the configuration of the values of available design tokens, following the
    # format outlined in https://github.com/amzn/style-dictionary#design-tokens which
    # is used by NLDS.
    # TODO: validate against the JSON build from @open-formulieren/design-tokens for
    # available tokens.
    # Example:
    # {
    #   "of": {
    #     "button": {
    #       "background-color": {
    #         "value": "fuchsia"
    #       }
    #     }
    #   }
    # }
    #
    design_token_values = models.JSONField(
        _("design token values"),
        blank=True,
        default=dict,
        help_text=_(
            "Values of various style parameters, such as border radii, background "
            "colors... Note that this is advanced usage. Any available but un-specified "
            "values will use fallback default values. See https://open-forms.readthedocs.io/en/latest"
            "/installation/form_hosting.html#run-time-configuration for documentation."
        ),
    )

    theme_classname = models.SlugField(
        _("theme CSS class name"),
        blank=True,
        help_text=_("If provided, this class name will be set on the <html> element."),
    )
    theme_stylesheet = models.URLField(
        _("theme stylesheet URL"),
        blank=True,
        max_length=1000,
        validators=[
            RegexValidator(
                regex=r"\.css$",
                message=_("The URL must point to a CSS resource (.css extension)."),
            ),
        ],
        help_text=_(
            "The URL stylesheet with theme-specific rules for your organization. "
            "This will be included as final stylesheet, overriding previously defined styles. "
            "Note that you also have to include the host to the `style-src` CSP directive. "
            "Example value: https://unpkg.com/@utrecht/design-tokens@1.0.0-alpha.20/dist/index.css."
        ),
    )

    # session timeouts

    admin_session_timeout = models.PositiveIntegerField(
        _("admin session timeout"),
        default=60,
        validators=[MinValueValidator(5)],
        help_text=_(
            "Amount of time in minutes the admin can be inactive for before being logged out"
        ),
    )
    form_session_timeout = models.PositiveIntegerField(
        _("form session timeout"),
        default=15,
        validators=[
            MinValueValidator(5),
            MaxValueValidator(
                15,
                message=_(
                    "Due to DigiD requirements this value has to be less than or equal to %(limit_value)s minutes."
                ),
            ),
        ],
        help_text=_(
            "Amount of time in minutes a user filling in a form can be inactive for before being logged out"
        ),
    )

    # global payment settings
    payment_order_id_prefix = models.CharField(
        _("Payment Order ID prefix"),
        max_length=16,
        default="{year}",
        blank=True,
        help_text=_(
            "Prefix to apply to generated numerical order IDs. Alpha-numerical only, supports placeholder {year}."
        ),
        validators=[validate_payment_order_id_prefix],
    )

    # analytics/tracking
    gtm_code = models.CharField(
        _("Google Tag Manager code"),
        max_length=50,
        blank=True,
        help_text=_(
            "Typically looks like 'GTM-XXXX'. Supplying this installs Google Tag Manager."
        ),
    )
    ga_code = models.CharField(
        _("Google Analytics code"),
        max_length=50,
        blank=True,
        help_text=_(
            "Typically looks like 'UA-XXXXX-Y'. Supplying this installs Google Analytics."
        ),
    )
    matomo_url = models.CharField(
        _("Matomo server URL"),
        max_length=255,
        blank=True,
        help_text=_("The base URL of your Matomo server, e.g. 'matomo.example.com'."),
    )
    matomo_site_id = models.PositiveIntegerField(
        _("Matomo site ID"),
        blank=True,
        null=True,
        help_text=_("The 'idsite' of the website you're tracking in Matomo."),
    )
    piwik_url = models.CharField(
        _("Piwik server URL"),
        max_length=255,
        blank=True,
        help_text=_("The base URL of your Piwik server, e.g. 'piwik.example.com'."),
    )
    piwik_site_id = models.PositiveIntegerField(
        _("Piwik site ID"),
        blank=True,
        null=True,
        help_text=_("The 'idsite' of the website you're tracking in Piwik."),
    )
    piwik_pro_url = models.CharField(
        _("Piwik PRO server URL"),
        max_length=255,
        blank=True,
        help_text=_(
            "The base URL of your Piwik PRO server, e.g. 'https://your-instance-name.piwik.pro/'."
        ),
    )
    piwik_pro_site_id = models.UUIDField(
        _("Piwik PRO site ID"),
        blank=True,
        null=True,
        help_text=_(
            "The 'idsite' of the website you're tracking in Piwik PRO. https://help.piwik.pro/support/questions/find-website-id/"
        ),
    )
    siteimprove_id = models.CharField(
        _("SiteImprove ID"),
        max_length=10,
        blank=True,
        help_text=_(
            "Your SiteImprove ID - you can find this from the embed snippet example, "
            "which should contain a URL like '//siteimproveanalytics.com/js/siteanalyze_XXXXX.js'. "
            "The XXXXX is your ID."
        ),
    )

    analytics_cookie_consent_group = models.ForeignKey(
        "cookie_consent.CookieGroup",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text=_(
            "The cookie group used for analytical cookies. The analytics scripts are "
            "loaded only if this cookie group is accepted by the end-user."
        ),
    )

    # Privacy policy related fields
    ask_privacy_consent = models.BooleanField(
        _("ask privacy consent"),
        default=True,
        help_text=_(
            "If enabled, the user will have to agree to the privacy policy before submitting a form."
        ),
    )
    privacy_policy_url = models.URLField(
        _("privacy policy URL"), blank=True, help_text=_("URL to the privacy policy")
    )
    privacy_policy_label = HTMLField(
        _("privacy policy label"),
        blank=True,
        help_text=_(
            "The label of the checkbox that prompts the user to agree to the privacy policy."
        ),
        default="Ja, ik heb kennis genomen van het {% privacy_policy %} en geef uitdrukkelijk "
        "toestemming voor het verwerken van de door mij opgegeven gegevens.",
    )

    # debug/feature flags
    enable_demo_plugins = models.BooleanField(
        _("enable demo plugins"),
        default=False,
        help_text=_("If enabled, the admin allows selection of demo backend plugins."),
    )

    default_test_bsn = models.CharField(
        _("default test BSN"),
        blank=True,
        default="",
        max_length=9,
        help_text=_(
            "When provided, submissions that are started will have this BSN set as "
            "default for the session. Useful to test/demo prefill functionality."
        ),
    )
    default_test_kvk = models.CharField(
        _("default test KvK Number"),
        blank=True,
        default="",
        max_length=9,
        help_text=_(
            "When provided, submissions that are started will have this KvK Number set as "
            "default for the session. Useful to test/demo prefill functionality."
        ),
    )

    display_sdk_information = models.BooleanField(
        _("display SDK information"),
        default=False,
        help_text=_("When enabled, information about the used SDK is displayed."),
    )

    # Removing data configurations
    successful_submissions_removal_limit = models.PositiveIntegerField(
        _("successful submission removal limit"),
        default=7,
        validators=[MinValueValidator(1)],
        help_text=_(
            "Amount of days successful submissions will remain before being removed"
        ),
    )
    successful_submissions_removal_method = models.CharField(
        _("successful submissions removal method"),
        max_length=50,
        choices=RemovalMethods,
        default=RemovalMethods.delete_permanently,
        help_text=_("How successful submissions will be removed after the limit"),
    )
    incomplete_submissions_removal_limit = models.PositiveIntegerField(
        _("incomplete submission removal limit"),
        default=7,
        validators=[MinValueValidator(1)],
        help_text=_(
            "Amount of days incomplete submissions will remain before being removed"
        ),
    )
    incomplete_submissions_removal_method = models.CharField(
        _("incomplete submissions removal method"),
        max_length=50,
        choices=RemovalMethods,
        default=RemovalMethods.delete_permanently,
        help_text=_("How incomplete submissions will be removed after the limit"),
    )
    errored_submissions_removal_limit = models.PositiveIntegerField(
        _("errored submission removal limit"),
        default=30,
        validators=[MinValueValidator(1)],
        help_text=_(
            "Amount of days errored submissions will remain before being removed"
        ),
    )
    errored_submissions_removal_method = models.CharField(
        _("errored submissions removal method"),
        max_length=50,
        choices=RemovalMethods,
        default=RemovalMethods.delete_permanently,
        help_text=_("How errored submissions will be removed after the"),
    )
    all_submissions_removal_limit = models.PositiveIntegerField(
        _("all submissions removal limit"),
        default=90,
        validators=[MinValueValidator(1)],
        help_text=_("Amount of days when all submissions will be permanently deleted"),
    )

    registration_attempt_limit = models.PositiveIntegerField(
        _("default registration backend attempt limit"),
        default=5,
        validators=[MinValueValidator(1)],
        help_text=_(
            "How often we attempt to register the submission at the registration backend before giving up"
        ),
    )

    plugin_configuration = models.JSONField(
        _("plugin configuration"),
        blank=True,
        default=dict,
        help_text=_(
            "Configuration of plugins for authentication, payments, prefill, "
            "registrations and validation"
        ),
    )
    enable_form_variables = models.BooleanField(
        _("enable form variables"),
        default=False,
        help_text=_("Whether to enable form variables in the form builder."),
    )

    class Meta:
        verbose_name = _("General configuration")

    def __str__(self):
        return force_str(self._meta.verbose_name)

    @property
    def matomo_enabled(self) -> bool:
        return self.matomo_url and self.matomo_site_id

    @property
    def piwik_enabled(self) -> bool:
        return self.piwik_url and self.piwik_site_id

    @property
    def piwik_pro_enabled(self) -> bool:
        return self.piwik_pro_url and self.piwik_pro_site_id

    @property
    def siteimprove_enabled(self) -> bool:
        return bool(self.siteimprove_id)

    def get_csp_updates(self):
        updates = defaultdict(list)
        if self.siteimprove_enabled:
            updates["default-src"].append("siteimproveanalytics.com")
            updates["img-src"].append("*.siteimproveanalytics.io")
        # TODO support more contributions
        return updates

    def render_privacy_policy_label(self):
        template = self.privacy_policy_label
        rendered_content = Template(template).render(Context({}))

        return rendered_content

    def plugin_enabled(self, module: str, plugin_identifier: str):
        enabled = glom(
            self.plugin_configuration,
            f"{module}.{plugin_identifier}.enabled",
            default=True,
        )
        return enabled


class RichTextColor(models.Model):
    color = ColorField(
        _("color"),
        format="hex",
        help_text=_("Color in RGB hex format (#RRGGBB)"),
    )
    label = models.CharField(
        _("label"),
        max_length=64,
        help_text=_("Human readable label for reference"),
    )

    class Meta:
        verbose_name = _("text editor color preset")
        verbose_name_plural = _("text editor color presets")
        ordering = ("label",)

    def __str__(self):
        return f"{self.label} ({self.color})"

    def example(self):
        return mark_safe(
            f'<span style="background-color: {self.color};">&nbsp; &nbsp; &nbsp;</span>'
        )

    example.short_description = _("Example")


class CSPSettingQuerySet(models.QuerySet):
    def as_dict(self):
        ret = defaultdict(set)
        for directive, value in self.values_list("directive", "value"):
            ret[directive].add(value)
        return {k: list(v) for k, v in ret.items()}


class CSPSetting(models.Model):
    directive = models.CharField(
        _("directive"),
        max_length=64,
        help_text=_("CSP header directive"),
        choices=CSPDirective.choices,
    )
    value = models.CharField(
        _("value"),
        max_length=128,
        help_text=_("CSP header value"),
    )

    objects = CSPSettingQuerySet.as_manager()

    class Meta:
        ordering = ("directive", "value")

    def __str__(self):
        return f"{self.directive} '{self.value}'"

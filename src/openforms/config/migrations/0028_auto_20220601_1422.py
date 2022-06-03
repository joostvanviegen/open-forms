# Generated by Django 3.2.13 on 2022-06-01 12:22

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0027_alter_cspsetting_directive"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalconfiguration",
            name="theme_classname",
            field=models.SlugField(
                blank=True,
                help_text="If provided, this class name will be set on the <html> element.",
                verbose_name="theme CSS class name",
            ),
        ),
        migrations.AddField(
            model_name="globalconfiguration",
            name="theme_stylesheet",
            field=models.URLField(
                blank=True,
                help_text="The URL stylesheet with theme-specific rules for your organization. This will be included as final stylesheet, overriding previously defined styles. Note that you also have to include the host to the `style-src` CSP directive. Example value: https://unpkg.com/@utrecht/design-tokens@1.0.0-alpha.20/dist/index.css.",
                max_length=1000,
                validators=[
                    django.core.validators.RegexValidator(
                        message="The URL must point to a CSS resource (.css extension).",
                        regex="\\.css$",
                    )
                ],
                verbose_name="theme stylesheet URL",
            ),
        ),
    ]

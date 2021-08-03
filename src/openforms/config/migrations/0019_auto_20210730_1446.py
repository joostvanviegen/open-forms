# Generated by Django 2.2.24 on 2021-07-30 12:46

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models

import openforms.utils.fields


class Migration(migrations.Migration):

    dependencies = [
        ("config", "0018_merge_20210726_1031"),
    ]

    operations = [
        migrations.AddField(
            model_name="globalconfiguration",
            name="design_token_values",
            field=django.contrib.postgres.fields.jsonb.JSONField(
                blank=True,
                default=dict,
                help_text="Values of various style parameters, such as border radii, background colors... Note that this is advanced usage. Any available but un-specified values will use fallback default values.",
                verbose_name="design token values",
            ),
        ),
        migrations.AddField(
            model_name="globalconfiguration",
            name="logo",
            field=openforms.utils.fields.SVGOrImageField(
                blank=True,
                help_text="Upload the municipality logo, visible to users filling out forms. We advise dimensions around 150px by 75px. SVG's are allowed.",
                upload_to="",
                verbose_name="municipality logo",
            ),
        ),
        migrations.AddField(
            model_name="globalconfiguration",
            name="main_website",
            field=models.URLField(
                blank=True,
                help_text="URL to the main website. Used for the 'back to municipality website' link.",
                verbose_name="main website link",
            ),
        ),
    ]

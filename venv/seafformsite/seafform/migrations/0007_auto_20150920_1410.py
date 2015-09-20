# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0006_form_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='form',
            name='formid',
            field=models.SlugField(serialize=False, max_length=40, primary_key=True),
            preserve_default=True,
        ),
    ]

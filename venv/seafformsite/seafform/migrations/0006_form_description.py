# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0005_form_reponame'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='description',
            field=models.CharField(max_length=1000, default='Some random description'),
            preserve_default=False,
        ),
    ]

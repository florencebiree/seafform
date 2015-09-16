# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('seafform', '0004_form_creation_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='form',
            name='reponame',
            field=models.CharField(default='', max_length=256),
            preserve_default=False,
        ),
    ]

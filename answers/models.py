# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# Create your models here.


class Question(models.Model):
    question_text = models.TextField()
    pub_date = models.DateTimeField('date published')
    link = models.TextField()


class Tag(models.Model):
    text = models.TextField()
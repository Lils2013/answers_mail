# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
from django.conf import settings
# Create your models here.


class Question(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # def __unicode__(self):
    #     result = '{0} {1}'.format(
    #         self.created_at.ctime(),
    #         self.text[:30])
    #     return result

    class Meta:
        ordering = ['created_at']


class Tag(models.Model):
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    questions = models.ManyToManyField(Question)
    #
    # def __unicode__(self):
    #     result = '{0} {1}'.format(
    #         self.created_at.ctime(),
    #         self.text[:30])
    #     return result

    class Meta:
        ordering = ['created_at']
# -*- coding: utf-8 -*-
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.shortcuts import get_object_or_404
from analytics.models import Tag
from answers_mail.permissions import permissions, ReadOnly
from serializers import TagSerializer


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all().order_by('-created')
    serializer_class = TagSerializer
    permission_classes = (ReadOnly, )

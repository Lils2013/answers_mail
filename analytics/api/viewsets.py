# -*- coding: utf-8 -*-
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from django.shortcuts import get_object_or_404
from analytics.models import Tag, Question
from answers_mail.permissions import permissions, ReadOnly
from serializers import TagSerializer, QuestionSerializer
from django.db.models import Count


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all().annotate(num_q=Count('questions')).order_by('-num_q')
    serializer_class = TagSerializer
    permission_classes = (ReadOnly, )


class QuestionsViewSet(ReadOnlyModelViewSet):
    queryset = Question.objects.all().order_by('-created_at')
    serializer_class = QuestionSerializer
    permission_classes = (ReadOnly, )
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
import datetime
import requests
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
# Create your views here.
from analytics.api.serializers import QuestionSerializer
from analytics.models import Question, Tag
import json


def import_data(request, page_from = -1, page_to = -1):
    now = datetime.datetime.now()
    html = "<html><body>It is now {}.</b> from: {} </b> to: {}</body></html>".format(now, page_from, page_to)
    if (page_to == -1):
        r = requests.get('https://otvet.mail.ru/api/v2/question?qid={}'.format(page_from))
        if (r.status_code == 200):
            # data = json.loads('{"lat":444, "lon":555}')
            html = "<html><body> {} </body></html>".format(r.text)

            # r.headers['content-type']
        # 'application/json; charset=utf8'
        #  r.encoding
        # 'utf-8'
        # >> > r.text
        # u'{"type":"User"...'
        # >> > r.json()
        # {u'private_gists': 419, u'total_private_repos': 77, ...}
    return HttpResponse(html)


@api_view(['GET'])
def tag_detail(request, pk):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        questions = Tag.objects.get(pk=pk).questions.all()
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


@api_view(['GET'])
def graph(request, pk):

    try:
        questions = Tag.objects.get(pk=pk).questions.all()
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = {}
        for question in questions:
            data[question.id] = question.id
        print(data)
        return Response(data)


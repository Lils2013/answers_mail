# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
import datetime, time
import requests
from analytics.models import Question, Tag
import json
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
# Create your views here.
from analytics.api.serializers import QuestionSerializer
from analytics.models import Question, Tag
import json


def roundTime(dt=None, roundTo=60):
    """Round a datetime object to any time lapse in seconds
   dt : datetime.datetime object, default now.
   roundTo : Closest number of seconds to round to, default 1 minute.
   Author: Thierry Husson 2012 - Use it as you want but don't blame me.
   """
    if dt == None: dt = datetime.datetime.now()
    seconds = (dt.replace(tzinfo=None) - dt.min).seconds
    rounding = (seconds + roundTo / 2) // roundTo * roundTo
    return dt + datetime.timedelta(0, rounding - seconds, -dt.microsecond)


def import_one(page_from):
    now = datetime.datetime.now()
    r = requests.get('https://otvet.mail.ru/api/v2/question?qid={}'.format(page_from))
    html = '{}'
    print('importing from {}'.format(page_from))
    if r.status_code == 200:
        data = r.json()
        question_text = data['qtext'] + ' ' + data['qcomment']

        bad_date = int(data['added'])
        ok_date = roundTime(datetime.datetime.fromtimestamp(time.mktime(now.timetuple()) - bad_date), 60 * 60 * 24)
        tag_list = data['category']['name']

        try:
            go = Question.objects.get(text=question_text)
            # go.delete()
            html = html.format('&emsp;{} - [FAILED] - Already exists<br/>'.format(page_from) + '{}')
            print('\t[FAILED] - Already exists\n')
            return html
        except Question.DoesNotExist:
            question = Question(text=question_text, created_at=ok_date, id=long(page_from))
            question.save()
            # for s_tag in tag_list:
            s_tag = tag_list  # ETO VREMENNO
            if Tag.objects.filter(text__exact=s_tag).count() == 0:
                tag = Tag(text=s_tag)
                tag.save()
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()
            else:
                tag = Tag.objects.get(text__exact=s_tag)
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()

                html = html.format('&emsp;{} - [OK]<br/>'.format(page_from) + '{}')
            print('\t[OK] - {} : <{}>\n'.format(ok_date, tag_list))

    else:
        print('\t[FAILED] - received code {}\n'.format(r.status_code))
        html = html.format('&emsp;{} - [FAILED] - received code {}<br/>'.format(page_from, r.status_code) + '{}')
    return html


def import_data(request, page_from=-1, page_to=-1):
    html = "<html><body><h4>Importing:</h4><br/>&emsp;from: {} <br/>&emsp;to: {} <br/> <h4>Results</h4> {}</body></html>".format(
        int(page_from), int(page_to), '{}')
    if page_to == -1:
        HttpResponse(import_one(page_from))
    elif page_from != -1 and page_to != -1:
        for i in range(int(page_from), int(page_to)):
            try:
                html = html.format(import_one(i))
            except Exception as e:
                html = html.format('&emsp;{} - [FAILED] - exception: {}<br/>'.format(i, e.message) + '{}')
                print('\t[FAILED] - exception: {}\n'.format(e.message))
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
        questions = Tag.objects.get(pk=pk).questions.all().order_by('-created_at')
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        data = {}
        for question in questions:
            if not data.has_key(question.created_at.date().isoformat()):
                data[question.created_at.date().isoformat()] = 1
            else:
                data[question.created_at.date().isoformat()] = data[question.created_at.date().isoformat()] + 1

        print(data)
        return Response(data)

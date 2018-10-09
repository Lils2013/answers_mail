# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
from datetime import datetime
import requests
from analytics.models import Question, Tag
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
# Create your views here.
from analytics.api.serializers import QuestionSerializer
from analytics.models import Question, Tag
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import csv
import re


def import_one(page_from):
    r = requests.get('https://otvet.mail.ru/api/v3/question/{}'.format(page_from), timeout=0.3)
    html = '{}'
    print('importing from {}'.format(page_from))
    if r.status_code == 200:
        data = r.json()
        question_text = data['text'] + ' ' + data['description']
        date_floor = datetime.strptime(data["created_at"].split("T")[0], "%Y-%m-%d")
        tag_title = data['category']['title']
        tag_id = int(data['category']['id'])

        try:
            go = Question.objects.get(id=page_from)
            html = html.format('&emsp;{} - [FAILED] - Already exists<br/>'.format(page_from) + '{}')
            print('\t[FAILED] - Already exists\n')
            return html
        except Question.DoesNotExist:
            question = Question(text=question_text, created_at=date_floor, id=long(page_from))
            question.save()
            try:
                tag = Tag.objects.get(id=tag_id)
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()
            except Tag.DoesNotExist:
                tag = Tag(id=tag_id, text=tag_title)
                tag.save()
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()

                # html = html.format('&emsp;{} - [OK]<br/>'.format(page_from) + '{}')
            print('\t[OK] - {} : <{}>\n'.format(date_floor, tag_title))

    else:
        print('\t[FAILED] - received code {}\n'.format(r.status_code))
        html = html.format('&emsp;{} - [FAILED] - received code {}<br/>'.format(page_from, r.status_code) + '{}')
    return html


def import_data(request, page_from=-1, page_to=-1):
    html = "<html><body><h4>Importing:</h4><br/>&emsp;from: {} <br/>&emsp;to: {} <br/> <h4>Results</h4> {}</body></html>".format(
        int(page_from), int(page_to), '{}')
    if page_from != -1 and page_to == -1:
        HttpResponse(import_one(page_from))
    elif page_from != -1 and page_to != -1:
        if page_to < page_from:
            tmp = page_to
            page_to = page_from
            page_from = tmp
        for i in range(int(page_from), int(page_to)):
            try:
                html = html.format(import_one(i))
            except Exception as e:
                html = html.format('&emsp;{} - [FAILED] - exception: {}<br/>'.format(i, e.message) + '{}')
                print('{}\t[FAILED] - exception: {}\n'.format(i, e.message))
            if i % (int(page_to) - int(page_from)) == 0:
                print("progress: {}%".format(i))
    else:
        html = "<html><body><h4>Не указан диапазон id, которые нужно скачать. Пример:</h4><br/> {}210700000-210701000</body></html>".format(
            request.get_raw_uri())
    return HttpResponse(html)


@api_view(['GET'])
def tag_detail(request, pk, page=1, page_size=10):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        questions = Tag.objects.get(pk=pk).questions.all()
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        paginator = Paginator(questions, page_size)
        serializer = QuestionSerializer(paginator.page(page), many=True)
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


@api_view(['GET'])
def tags(request, page=1, page_size=10):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        tags = sorted(Tag.objects.all(), key=lambda i: i.questions.count(), reverse=True)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        paginator = Paginator(tags, page_size)
        serializer = QuestionSerializer(paginator.page(page), many=True)
        return Response(serializer.data)


def import_from_dump(request):
    with open("otvet-queastions-2018-2.txt") as tsvfile:
        for line in tsvfile:
            # print(line)
            line_data = re.split('\t', line)
            question_text = line_data[9].rstrip().lstrip()
            if (len(line_data) == 11):
                question_text += line_data[10].rstrip().lstrip()
            created_at = datetime.strptime(line_data[1].split(" ")[0], "%Y-%m-%d")
            question = Question(text=question_text, created_at=created_at, id=int(line_data[0]))
            # print(question.text)
            question.save()
            try:
                tag = Tag.objects.get(id=int(line_data[5]))
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()
            except Tag.DoesNotExist:
                tag = Tag(id=int(line_data[5]), text=line_data[6])
                tag.save()
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()

            # print '-----'
            # print line
            # print line_data
            # print line_data[0]
            # print line_data[1]
            # print line_data[2]
            # print line_data[3]
            # print line_data[4]
            # print line_data[5]
            # print line_data[6]
            # print line_data[7]
            # print line_data[8]
            # print line_data[9]
            # if (len(line_data) == 11):
            #      print line_data[10]

    return HttpResponse("<html><body><h4>Lol</h4></body></html>")

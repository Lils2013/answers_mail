# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from datetime import datetime, timedelta

import pytz
import requests
from django.core.paginator import Paginator
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Create your views here.
from analytics.api.serializers import QuestionSerializer
from analytics.models import Category
from analytics.models import Question, Tag


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
def tag_detail(request, pk, page=1, page_size=50):
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
def graph(request, pk, time_interval):
    if request.method == 'GET':
        try:
            questions = Tag.objects.get(pk=pk).questions.all().order_by('-created_at')
        except Tag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = {}
        if time_interval == '1-d':
            end_date = datetime.strptime('2018-02-02T00:00:00', "%Y-%m-%dT%H:%M:%S")
            timezone = pytz.timezone("Europe/Moscow")
            end_date = timezone.localize(end_date)
            start_date = end_date - timedelta(days=1)
            questions = questions.filter(created_at__range=(start_date, end_date))
            for i in range(24 * 1):
                data[(start_date.replace(minute=0, second=0) + timedelta(hours=i + 1)).isoformat()] = 0
            for question in questions:
                datetime_hour = (question.created_at.astimezone(timezone).replace(minute=0, second=0) + timedelta(
                    hours=1)).isoformat()
                if not data.has_key(datetime_hour):
                    data[datetime_hour] = 1
                else:
                    data[datetime_hour] = data[datetime_hour] + 1
        elif time_interval == '7-d':
            end_date = datetime.strptime('2018-02-02T00:00:00', "%Y-%m-%dT%H:%M:%S")
            timezone = pytz.timezone("Europe/Moscow")
            end_date = timezone.localize(end_date)
            start_date = end_date - timedelta(days=7)
            questions = questions.filter(created_at__range=(start_date, end_date))
            for i in range(6 * 7):
                data[(start_date.replace(minute=0, second=0) + timedelta(hours=i * 4 + 4)).isoformat()] = 0
            for question in questions:
                datetime_hour = (question.created_at.astimezone(timezone).replace(minute=0, second=0) + timedelta(
                    hours=4)).isoformat()
                if not data.has_key(datetime_hour):
                    data[datetime_hour] = 1
                else:
                    data[datetime_hour] = data[datetime_hour] + 1
        elif time_interval == '1-m':
            end_date = datetime.strptime('2018-02-02', "%Y-%m-%d")
            timezone = pytz.timezone("Europe/Moscow")
            end_date = timezone.localize(end_date)
            start_date = end_date - timedelta(days=30)
            questions = questions.filter(created_at__range=(start_date, end_date))
            for question in questions:
                date_with_tz = question.created_at.astimezone(timezone).date().isoformat()
                if not data.has_key(date_with_tz):
                    data[date_with_tz] = 1
                else:
                    data[date_with_tz] = data[date_with_tz] + 1
        else:
            timezone = pytz.timezone("Europe/Moscow")
            for question in questions:
                date_with_tz = question.created_at.astimezone(timezone).date().isoformat()
                if not data.has_key(date_with_tz):
                    data[date_with_tz] = 1
                else:
                    data[date_with_tz] = data[date_with_tz] + 1
        return Response(data)


@api_view(['GET'])
def tags(request, page=1, page_size=50):
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
                question_text += ' '.encode('utf-8') + line_data[10].rstrip().lstrip()
            created_at = datetime.strptime(line_data[1], "%Y-%m-%d %H:%M:%S")
            timezone = pytz.timezone("Europe/Moscow")
            created_at = timezone.localize(created_at)
            # print(created_at.isoformat())
            question = Question(text=question_text, rating=int(line_data[2]), created_at=created_at,
                                id=int(line_data[0]))
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
            try:
                tag = Tag.objects.get(id=int(line_data[7]))
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()
            except Tag.DoesNotExist:
                tag = Tag(id=int(line_data[7]), text=line_data[8])
                tag.save()
                tag.questions.add(Question.objects.get(id=question.id))
                tag.save()
            try:
                category = Category.objects.get(id=int(line_data[5]))
                category.questions.add(Question.objects.get(id=question.id))
                category.save()
            except Category.DoesNotExist:
                category = Category(id=int(line_data[5]), name=line_data[6])
                category.save()
                category.questions.add(Question.objects.get(id=question.id))
                category.save()
            try:
                category = Category.objects.get(id=int(line_data[7]))
                category.questions_parent.add(Question.objects.get(id=question.id))
                category.save()
            except Category.DoesNotExist:
                category = Category(id=int(line_data[7]), name=line_data[8])
                category.save()
                category.questions_parent.add(Question.objects.get(id=question.id))
                category.save()

    return HttpResponse("<html><body><h4>Lol</h4></body></html>")

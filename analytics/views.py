# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import re
from datetime import datetime, timedelta

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
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import csv
import re
import json


def get_api_page(page_from, page_size):
    url = 'https://otvet.mail.ru/api/v3/questions?limit={}&start_id={}'.format(page_size, page_from)
    r = requests.get(url)
    if r.status_code == 200:
        # print(r.text)
        return r.json()
    else:
        raise Exception("server response code {} \n from url: {}".format(r.status_code, url))


def parse_and_save_question(data):
    question_text = data['text'] + ' ' + data['description']
    # date_floor = datetime.strptime(data["created_at"].split("T")[0], "%Y-%m-%d")
    date_floor = datetime.strptime(data["created_at"].split('+')[0], "%Y-%m-%dT%H:%M:%S")
    tag_title = data['category']['title']
    tag_id = int(data['category']['id'])
    qid = int(data['id'])

    try:
        check_if_exists = Question.objects.get(id=qid)
        return 'already exists'
    except Question.DoesNotExist:
        question = Question(text=question_text, created_at=date_floor, id=qid)
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
        return tag_title


def update_and_show_status(report, current_status):
    for k, v in current_status.iteritems():
        if report.get(k) is None:
            report[k] = v
        else:
            report[k] = report[k] + v
    sorted_by_value = sorted(current_status.items(), key=lambda kv: kv[1],  reverse=True)
    length = min(10, len(sorted_by_value))
    for i in range(length):
        print("{}: {}".format(sorted_by_value[i][1], sorted_by_value[i][0]))
    return report


def import_from_api(page_from, amount):
    page_size = 1000
    pages = int(amount / page_size)
    last_page_size = amount % page_size
    html = '{}'
    report = {}
    try:
        if pages != 0:
            for i in range(pages+1):
                current_status = {}
                if i == pages:
                    page_size = last_page_size
                try:
                    data = get_api_page(page_from, page_size)
                except Exception as e:
                    print("***** PROGRESS *****")
                    print("page: {}/{}".format(i+1, pages+1))
                    print("Error: {}".format(e.message))
                    page_from += page_size
                    continue
                if len(data) == 0:
                    print("Вопросы-то кончились!")
                    break
                for q in data:
                    result = parse_and_save_question(q)
                    if current_status.get(result) is None:
                        current_status[result] = 1
                    else:
                        current_status[result] += 1
                    page_from = int(q['id'])

                print("***** PROGRESS *****")
                print("page: {}/{}".format(i+1, pages+1))
                report = update_and_show_status(report, current_status)
                print("\n")
    finally:
        sorted_by_value = sorted(report.items(), key=lambda kv: kv[1], reverse=True)
        for (k, v) in sorted_by_value:
            html = html.format('{}  -  [{}] <br/> {}'.format(v, k, "{}"))
    return html

# 210800000-88111


def import_from_api_view(request, page_from=-1, page_to=-1, amount=-1):
    html = "<html><body><h4>Importing:</h4>" \
           "<br/>&emsp;from: {} " \
           "<br/>&emsp;amount: {} " \
           "<br/> <h4>Results</h4> time: {} " \
           "<br/>{}</body></html>"
    page_from = int(page_from)
    page_to = int(page_to)
    amount = int(amount)
    start_time = datetime.now()

    if page_from != -1 and page_to == -1 and amount != -1:
        info = import_from_api(page_from, amount)
        work_time = datetime.now() - start_time
        html = html.format(page_from, amount, str(work_time).split('.')[0] ,info)
    else:
        html = "<html><body><h4>Не указан диапазон id, которые нужно скачать. Пример:</h4>" \
               "<br/>page_from-amount:  {}210700000-1000</body></html>".format(
            request.get_raw_uri(), request.get_raw_uri())
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
def graph(request, pk, time_interval):
    if request.method == 'GET':
        try:
            questions = Tag.objects.get(pk=pk).questions.all().order_by('-created_at')
        except Tag.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        data = {}
        if time_interval == '1-d':
            # end_date = datetime.today()
            end_date = datetime.strptime('2018-02-02', "%Y-%m-%d")
            start_date = end_date - timedelta(days=1)
            questions = questions.filter(created_at__range=(start_date, end_date))
            for question in questions:
                datetime_hour = (question.created_at.replace(minute=0, second=0) + timedelta(hours=1)).strftime(
                    "%Y-%m-%d %H:%M:%S")
                if not data.has_key(datetime_hour):
                    data[datetime_hour] = 1
                else:
                    data[datetime_hour] = data[datetime_hour] + 1
        elif time_interval == '7-d':
            # end_date = datetime.today()
            end_date = datetime.strptime('2018-02-02', "%Y-%m-%d")
            start_date = end_date - timedelta(days=7)
            questions = questions.filter(created_at__range=(start_date,end_date))
            for question in questions:
                datetime_hour = (question.created_at.replace(minute=0, second=0) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
                if not data.has_key(datetime_hour):
                    data[datetime_hour] = 1
                else:
                    data[datetime_hour] = data[datetime_hour] + 1
        elif time_interval == '1-m':
            # end_date = datetime.today()
            end_date = datetime.strptime('2018-02-02', "%Y-%m-%d")
            start_date = end_date - timedelta(days=30)
            questions = questions.filter(created_at__range=(start_date,end_date))
            for question in questions:
                if not data.has_key(question.created_at.date().isoformat()):
                    data[question.created_at.date().isoformat()] = 1
                else:
                    data[question.created_at.date().isoformat()] = data[question.created_at.date().isoformat()] + 1
        else:
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
                question_text += ' '.encode('utf-8') + line_data[10].rstrip().lstrip()
            created_at = datetime.strptime(line_data[1], "%Y-%m-%d %H:%M:%S")
            question = Question(text=question_text, rating=int(line_data[2]), created_at=created_at, id=int(line_data[0]))
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

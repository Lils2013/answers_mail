# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import pytz
from django.db.models import F, Sum
from django.db import connection
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Create your views here.
from analytics.api.serializers import QuestionSerializer, TagSerializer, CategorySerializer
from analytics.models import Category, Counter
from analytics.models import Question, Tag
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
import re
from .utils import import_from_api
import dateutil.parser


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
        html = html.format(page_from, amount, str(work_time).split('.')[0], info)
    else:
        html = "<html><body><h4>Не указан диапазон id, которые нужно скачать. Пример:</h4>" \
               "<br/>page_from-amount:  {}210700000-1000</body></html>".format(
            request.get_raw_uri(), request.get_raw_uri())
    return HttpResponse(html)


@api_view(['GET'])
def tag_detail(request, pk, page=1, page_size=50):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        questions = Tag.objects.get(pk=pk).questions.all()[:page_size]
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # paginator = Paginator(questions, page_size)
        serializer = QuestionSerializer(questions, many=True)
        return Response(serializer.data)


@api_view(['GET'])
def get_questions(request, page_size=50):
    tagid = request.GET.get('tagid', None)
    if tagid is None:
        return Response({'status': 500, 'error': 'no tagid'})
    try:
        tagid = int(tagid)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect tagid'})
    # timezone = pytz.timezone("Europe/Moscow")
    # time_interval = request.GET.get('date', None)
    # if time_interval is None:
    #     return Response({'status': 500, 'error': 'no date'})
    category_id = request.GET.get('catid', None)
    if category_id == '':
        category_id = None
    try:
        if category_id is not None:
            category_id = int(category_id)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect catid'})
    try:
        # Question.objects.all().filter(category_id=category_id, tags__id=tagid)
        questions = Question.objects.all().filter(tags__id=tagid)
        if category_id is not None:
            questions = questions.filter(category_id=category_id)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # paginator = Paginator(questions, page_size)
        serializer = QuestionSerializer(questions[:page_size], many=True)
        return Response(serializer.data)


@api_view(['GET'])
def graphs(request):
    tags = request.GET.getlist('tags[]', None)
    if tags is None:
        return Response({'status': 500, 'error': 'no tags'})
    try:
        tags = map(int, tags)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect tags'})
    timezone = pytz.timezone("Europe/Moscow")
    time_interval = request.GET.get('date', None)
    if time_interval is None:
        return Response({'status': 500, 'error': 'no date'})
    category_id = request.GET.get('catid', None)
    if category_id == '':
        category_id = None
    try:
        if category_id is not None:
            category_id = int(category_id)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect catid'})
    data = []
    try:
        start_date, end_date = time_interval.split(" ")
        # end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S")
        end_date = dateutil.parser.parse(end_date)
        start_date = dateutil.parser.parse(start_date)
        end_date = end_date.astimezone(timezone)
        start_date = start_date.astimezone(timezone)
        for tag in tags:
            data_for_tag = {}
            for i in range((end_date - start_date).days + 1):
                date_iter_start = start_date + timedelta(hours=24 * i)
                date_iter_end = date_iter_start + timedelta(hours=24)
                counters = Counter.objects.all().filter(
                    datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=tag)
                if (category_id is not None):
                    counters = counters.filter(category_id=category_id)
                if counters:
                    data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                        'num_of_questions']
                else:
                    data_for_tag[date_iter_start.isoformat()] = 0
            data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
    except ValueError as er:
        if time_interval == 'now 1-d':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=1)
            for tag in tags:
                data_for_tag = {}
                for i in range(24 * 1):
                    date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i)
                    date_iter_end = date_iter_start + timedelta(hours=1)
                    counters = Counter.objects.all().filter(datetime=date_iter_end, tag_id=tag)
                    if (category_id is not None):
                        counters = counters.filter(category_id=category_id)
                    if counters:
                        data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                            'num_of_questions']
                    else:
                        data_for_tag[date_iter_start.isoformat()] = 0
                data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
        elif time_interval == 'now 7-d':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=7)
            for tag in tags:
                data_for_tag = {}
                for i in range(6 * 7):
                    date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=4 * i)
                    date_iter_end = date_iter_start + timedelta(hours=4)
                    counters = Counter.objects.all().filter(datetime__in=(
                        date_iter_end, date_iter_end - timedelta(hours=1), date_iter_end - timedelta(hours=2),
                        date_iter_end - timedelta(hours=3)), tag_id=tag)
                    if (category_id is not None):
                        counters = counters.filter(category_id=category_id)
                    if counters:
                        data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                            'num_of_questions']
                    else:
                        data_for_tag[date_iter_start.isoformat()] = 0
                data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
        elif time_interval == 'now 1-m':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=30)
            for tag in tags:
                data_for_tag = {}
                for i in range(30):
                    date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=24 * i)
                    date_iter_end = date_iter_start + timedelta(hours=24)
                    counters = Counter.objects.all().filter(
                        datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=tag)
                    if (category_id is not None):
                        counters = counters.filter(category_id=category_id)
                    if counters:
                        data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                            'num_of_questions']
                    else:
                        data_for_tag[date_iter_start.isoformat()] = 0
                data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
        elif time_interval == 'now 1-y':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=365)
            for tag in tags:
                data_for_tag = {}
                for i in range(365):
                    date_iter_start = start_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=24 * i)
                    date_iter_end = date_iter_start + timedelta(hours=24)
                    counters = Counter.objects.all().filter(
                        datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=tag)
                    if (category_id is not None):
                        counters = counters.filter(category_id=category_id)
                    if counters:
                        data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                            'num_of_questions']
                    else:
                        data_for_tag[date_iter_start.isoformat()] = 0
                data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
        else:
            for tag in tags:
                data_for_tag = {}
                counters = Counter.objects.all().filter(tag_id=tag)
                if (category_id is not None):
                    counters = counters.filter(category_id=category_id)
                for counter in counters:
                    date_with_tz = (counter.datetime.astimezone(timezone) - timedelta(hours=1)).replace(hour=0, minute=0,
                                                                                                        second=0).isoformat()
                    if not data_for_tag.has_key(date_with_tz):
                        data_for_tag[date_with_tz] = counter.count
                    else:
                        data_for_tag[date_with_tz] = data_for_tag[date_with_tz] + counter.count
                data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
    return Response(data)


@api_view(['GET'])
def tags(request, page=1, page_size=50):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT at.text as text, ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                           "INNER JOIN analytics_tag at ON ac.tag_id = at.id "
                           "GROUP BY ac.tag_id, at.text ORDER BY SUM(ac.count) DESC LIMIT 50")
            rows = dictfetchall(cursor)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(rows)


@api_view(['GET'])
def tags_with_category(request, pk):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT at.text as text, ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                           "INNER JOIN analytics_tag at ON ac.tag_id = at.id WHERE ac.category_id = %s "
                           "GROUP BY ac.tag_id, at.text ORDER BY SUM(ac.count) DESC LIMIT 50",[pk])
            rows = dictfetchall(cursor)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        return Response(rows)


@api_view(['GET'])
def categories(request, page=1, page_size=50):
    try:
        categories = sorted(Category.objects.all(),
                      key=lambda i: i.questions_count,
                      reverse=True)
    except Category.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # paginator = Paginator(categories, page_size)
        serializer = CategorySerializer(categories, many=True)
        return Response(serializer.data)


def dictfetchall(cursor):
    "Return all rows from a cursor as a dict"
    columns = [col[0] for col in cursor.description]
    return [
        dict(zip(columns, row))
        for row in cursor.fetchall()
    ]
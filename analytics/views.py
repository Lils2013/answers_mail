# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import pytz
from django.db.models import F, Sum, Count
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
from .utils import import_from_api, get_request_cache, set_request_cache
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


def parse_date(time_interval):
    timezone = pytz.timezone("Europe/Moscow")
    days = 0
    try:
        start_date, end_date = time_interval.split(" ")
        # end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S")
        end_date = dateutil.parser.parse(end_date)
        start_date = dateutil.parser.parse(start_date)
        end_date = end_date.astimezone(timezone)
        start_date = start_date.astimezone(timezone)
        days = (end_date - start_date).days
        if start_date == end_date:
            end_date = end_date + timedelta(days=1)
            days = 1
    except ValueError as er:
        end_date = datetime.now(pytz.utc)
        end_date = end_date.astimezone(timezone)
        if time_interval == 'now 1-d':
            start_date = end_date - timedelta(days=1)
            days = 1
        elif time_interval == 'now 7-d':
            start_date = end_date - timedelta(days=7)
            days = 7
        elif time_interval == 'now 1-m':
            start_date = end_date - timedelta(days=30)
            days = 30
        elif time_interval == 'now 1-y':
            start_date = end_date - timedelta(days=365)
            days = 365
        else:
            start_date = None
    return start_date, end_date, days


@api_view(['GET'])
def get_questions(request, page_size=50):
    tags = request.GET.getlist('tags[]', None)
    if tags is None:
        return Response({'status': 500, 'error': 'no tags'})
    try:
        tags = map(int, tags)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect tags'})
    # tagid = request.GET.get('tagid', None)
    # if tagid is None:
    #     return Response({'status': 500, 'error': 'no tagid'})
    # try:
    #     tagid = int(tagid)
    # except ValueError:
    #     return Response({'status': 500, 'error': 'incorrect tagid'})
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

    cached_data = get_request_cache("get_questions", [time_interval, category_id, tags])
    if cached_data is not None and request.method == 'GET':
        return Response(cached_data)

    try:
        # Question.objects.all().filter(category_id=category_id, tags__id=tagid)
        start_date, end_date, _ = parse_date(time_interval)
        if start_date is None:
            questions = Question.objects.all().filter(tags__in=tags).annotate(num_tags=Count('tags')).filter(num_tags=len(tags)).order_by('-created_at')
        else:
            questions = Question.objects.all().filter(tags__in=tags, created_at__range=(start_date, end_date)).annotate(num_tags=Count('tags')).filter(num_tags=len(tags)).order_by('-created_at')
        if category_id is not None:
            questions = questions.filter(category_id=category_id).order_by('-created_at')
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        # paginator = Paginator(questions, page_size)
        serializer = QuestionSerializer(questions[:page_size], many=True)
        set_request_cache("get_questions", serializer.data, [time_interval, category_id, tags])
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

    # points per days
    ppd = {0: 0.1, 1: 24, 7: 6, 30: 1, 365: 0.1}

    start_date, end_date, days = parse_date(time_interval)
    if days is None or (ppd.get(days) is None and days < 30):
        points_per_day = 1
    elif ppd.get(days) is None and (30 <= days < 180):
        points_per_day = 0.5
    elif ppd.get(days) is None and (180 <= days < 360):
        points_per_day = 0.2
    elif ppd.get(days) is None and days >= 360:
        points_per_day = 0.1
    else:
        points_per_day = ppd[days]

    cached_data = get_request_cache("graphs", [tags, days, points_per_day, category_id, start_date, end_date])
    if cached_data is not None:
        return Response(cached_data)

    data = get_last_graph_data(tags, days, points_per_day, category_id=category_id, start_date=start_date, end_date=end_date, only_existing_data=False)

    set_request_cache("graphs", data, [tags, days, points_per_day, category_id, start_date, end_date])
    return Response(data)


@api_view(['GET'])
def tags(request):
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
    sort_type = request.GET.get('sortType', None)
    if sort_type not in ['idf', 'qcount']:
        return Response({'status': 500, 'error': 'incorrect sort_type'})
    start_date, end_date, _ = parse_date(time_interval)

    rows = get_request_cache("tags", [time_interval, category_id, sort_type])
    if rows is not None and request.method == 'GET':
        return Response(rows)

    with connection.cursor() as cursor:
        if start_date is None:
            if category_id is None:
                cursor.execute(
                    "SELECT at.text, t1.id, t1.questions_count FROM "
                    "(SELECT  ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                    "GROUP BY ac.tag_id ORDER BY SUM(ac.count) DESC LIMIT 50) t1 "
                    "INNER JOIN analytics_tag at ON t1.id = at.id WHERE at.questions_count > 10")
            else:
                cursor.execute(
                    "SELECT at.text, t1.id, t1.questions_count FROM "
                    "(SELECT  ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                    "WHERE ac.category_id = %s "
                    "GROUP BY ac.tag_id ORDER BY SUM(ac.count) DESC LIMIT 50) t1 "
                    "INNER JOIN analytics_tag at ON t1.id = at.id WHERE at.questions_count > 10 ", [category_id])
        else:
            if category_id is None:
                cursor.execute(
                    "SELECT at.text, t1.id, t1.questions_count FROM "
                    "(SELECT  ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                    "WHERE ac.datetime > %s AND ac.datetime < %s  "
                    "GROUP BY ac.tag_id ORDER BY SUM(ac.count) DESC LIMIT 50) t1 "
                    "INNER JOIN analytics_tag at ON t1.id = at.id WHERE at.questions_count > 10 ", [start_date, end_date])
            else:
                cursor.execute(
                    "SELECT at.text, t1.id, t1.questions_count FROM "
                    "(SELECT  ac.tag_id as id, SUM(ac.count) AS questions_count FROM analytics_counter ac "
                    "WHERE ac.category_id = %s AND ac.datetime > %s AND ac.datetime < %s  "
                    "GROUP BY ac.tag_id ORDER BY SUM(ac.count) DESC LIMIT 50) t1 "
                    "INNER JOIN analytics_tag at ON t1.id = at.id WHERE at.questions_count > 10 ", [category_id, start_date, end_date])
        rows = dictfetchall(cursor)

    set_request_cache("tags", rows, [time_interval, category_id, sort_type])
    if request.method == 'GET':
        return Response(rows)


@api_view(['GET'])
def tags_search(request):
    search_text = request.GET.get('searchText', None)
    try:
        tags = sorted(Tag.objects.all().filter(questions_count__gt=10, text__icontains=search_text),
                      key=lambda i: i.questions_count,
                      reverse=True)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = TagSerializer(tags[:50], many=True)
        return Response(serializer.data)


@api_view(['GET'])
def categories(request, page=1, page_size=50):
    try:
        categories = sorted(Category.objects.all(),
                      key=lambda i: i.name)
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


# if days = 0 it will return data for all time
def get_last_graph_data(tags, days, points_per_day, category_id=None, start_date=None, end_date=None, only_existing_data=False):
    timezone = pytz.timezone("Europe/Moscow")
    if start_date is None or end_date is None:
        end_date = datetime.now(pytz.utc)
        end_date = end_date.astimezone(timezone)
        start_date = end_date - timedelta(days=days)
    if only_existing_data:
        counters = Counter.objects.all().filter(tag_id=tags[0])
        if category_id is not None:
            counters = counters.filter(category_id=category_id)
        end_date = counters.order_by('-datetime')[0].datetime
        start_date = end_date - timedelta(days=days)
        pass
    delta_hours = 24 / points_per_day
    # print(timedelta(hours=delta_hours))
    data = []
    for tag in tags:
        data_for_tag = {}
        # data for all time
        if days == 0:
            counters = Counter.objects.all().filter(tag_id=tag)
            if category_id is not None:
                counters = counters.filter(category_id=category_id)
            for counter in counters:
                date_with_tz = (counter.datetime.astimezone(timezone) - timedelta(hours=1)).replace(hour=0, minute=0,
                                                                                                    second=0).isoformat()
                if not data_for_tag.has_key(date_with_tz):
                    data_for_tag[date_with_tz] = counter.count
                else:
                    data_for_tag[date_with_tz] = data_for_tag[date_with_tz] + counter.count
        else:
            for i in range(int(days * points_per_day)):
                date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=delta_hours * i)
                date_iter_end = date_iter_start + timedelta(hours=delta_hours)
                counters = Counter.objects.all().filter(
                    datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=tag)
                if category_id is not None:
                    counters = counters.filter(category_id=category_id)
                if counters:
                    data_for_tag[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                        'num_of_questions']
                else:
                    data_for_tag[date_iter_start.isoformat()] = 0
        data.append({'data': data_for_tag, 'name': Tag.objects.get(pk=tag).text})
    return data

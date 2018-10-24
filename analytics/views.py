# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from datetime import datetime, timedelta
import pytz
from django.db.models import F, Sum
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

# Create your views here.
from analytics.api.serializers import QuestionSerializer
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
def graph(request):
    pk = request.GET.get('tagid', None)
    if pk is None:
        return Response({'status': 500, 'error': 'no tagid'})
    try:
        pk = int(pk)
    except ValueError:
        return Response({'status': 500, 'error': 'incorrect tagid'})
    timezone = pytz.timezone("Europe/Moscow")
    time_interval = request.GET.get('date', None)
    data = {}
    try:
        start_date, end_date = time_interval.split(" ")
        # end_date = datetime.strptime(end_date, "%Y-%m-%dT%H:%M:%S")
        end_date = dateutil.parser.parse(end_date)
        start_date = dateutil.parser.parse(start_date)
        end_date = end_date.astimezone(timezone)
        start_date = start_date.astimezone(timezone)
        for i in range((end_date - start_date).days + 1):
            date_iter_start = start_date + timedelta(hours=24 * i)
            date_iter_end = date_iter_start + timedelta(hours=24)
            counters = Counter.objects.all().filter(
                datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=pk)
            if counters:
                data[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                    'num_of_questions']
            else:
                data[date_iter_start.isoformat()] = 0
    except ValueError as er:
        if time_interval == 'now 1-d':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=1)
            for i in range(24 * 1):
                date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i)
                date_iter_end = date_iter_start + timedelta(hours=1)
                counters = Counter.objects.all().filter(datetime=date_iter_end, tag_id=pk)
                if counters:
                    data[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                        'num_of_questions']
                else:
                    data[date_iter_start.isoformat()] = 0
        elif time_interval == 'now 7-d':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=7)
            for i in range(6 * 7):
                date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=4 * i)
                date_iter_end = date_iter_start + timedelta(hours=4)
                counters = Counter.objects.all().filter(datetime__in=(
                    date_iter_end, date_iter_end - timedelta(hours=1), date_iter_end - timedelta(hours=2),
                    date_iter_end - timedelta(hours=3)), tag_id=pk)
                if counters:
                    data[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                        'num_of_questions']
                else:
                    data[date_iter_start.isoformat()] = 0
        elif time_interval == 'now 1-m':
            end_date = datetime.now(pytz.utc)
            end_date = end_date.astimezone(timezone)
            start_date = end_date - timedelta(days=30)
            for i in range(30):
                date_iter_start = start_date.replace(minute=0, second=0, microsecond=0) + timedelta(hours=24 * i)
                date_iter_end = date_iter_start + timedelta(hours=24)
                counters = Counter.objects.all().filter(
                    datetime__range=(date_iter_start + timedelta(hours=1), date_iter_end), tag_id=pk)
                if counters:
                    data[date_iter_start.isoformat()] = counters.aggregate(num_of_questions=Sum('count'))[
                        'num_of_questions']
                else:
                    data[date_iter_start.isoformat()] = 0
        else:
            for counter in Counter.objects.all().filter(tag_id=pk):
                date_with_tz = (counter.datetime.astimezone(timezone) - timedelta(hours=1)).replace(hour=0, minute=0,
                                                                                                    second=0).isoformat()
                if not data.has_key(date_with_tz):
                    data[date_with_tz] = counter.count
                else:
                    data[date_with_tz] = data[date_with_tz] + counter.count
    data_with_name = {'data': data, 'name': Tag.objects.get(pk=pk).text}
    return Response([data_with_name])


@api_view(['GET'])
def tags(request, page=1, page_size=50):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        tags = sorted(Tag.objects.all(),
                      key=lambda i: i.questions_count,
                      reverse=True)
    except Tag.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        paginator = Paginator(tags, page_size)
        serializer = QuestionSerializer(paginator.page(page), many=True)
        return Response(serializer.data)

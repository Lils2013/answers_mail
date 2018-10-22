# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz
import requests
from django.db.models import F

from analytics.models import Question, Category, Tag, Counter
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def get_api_page(page_from, page_size):
    # url = 'https://otvet.mail.ru/api/v3/questions?limit={}&start_id={}'.format(page_size, page_from)
    url = 'https://otvet.mail.ru/api/v3/question/{}'.format(page_from)
    r = requests.get(url)
    if r.status_code == 200:
        # print(r.text)
        return r.json()
    else:
        raise Exception("server response code {} \n from url: {}".format(r.status_code, url))


def get_api(id):
    url = 'https://otvet.mail.ru/api/v3/question/{}'.format(id)
    r = requests.get(url)
    if r.status_code == 200:
        # print(r.text)
        return r.json()
    else:
        raise Exception("server response code {} \n from url: {}".format(r.status_code, url))


def parse_question(data):
    question_text = data['text'] + ' ' + data['description']
    # date_floor = datetime.strptime(data["created_at"].split("T")[0], "%Y-%m-%d")
    date_floor = datetime.strptime(data["created_at"].split('+')[0], "%Y-%m-%dT%H:%M:%S")
    timezone = pytz.timezone("Europe/Moscow")
    date_floor = timezone.localize(date_floor)
    rating = int(data['mark_count'])
    cat_title = data['category']['title']
    cat_id = int(data['category']['id'])
    qid = int(data['id'])
    return dict(id=qid, text=question_text, date=date_floor, cat_title=cat_title, cat_id=cat_id, rating=rating)


def update_counter(qdata):
    counter = Counter.objects.all().filter(category=Category.objects.get(id=qdata['cat_id']), tag=Tag.objects.get(id=qdata['cat_id']),
                                           datetime=qdata['date'].replace(minute=0, second=0)
                                                    + timedelta(hours=1))
    if not counter:
        counter = Counter(category=Category.objects.get(id=qdata['cat_id']), tag=Tag.objects.get(id=qdata['cat_id']),
                                           datetime=qdata['date'].replace(minute=0, second=0)
                                                    + timedelta(hours=1), count=1)
        counter.save()
    else:
        counter = counter[0]
        counter.count = F('count') + 1
        counter.save()


def save_question(qdata):
    try:
        question = Question.objects.get(id=qdata['id'])
        return 'already exists'
    except Question.DoesNotExist:
        question = Question(text=qdata['text'], created_at=qdata['date'], id=qdata['id'], rating=qdata['rating'])
        question.save()
        try:
            category = Category.objects.get(id=qdata['cat_id'])
            category.questions.add(Question.objects.get(id=question.id))
            category.save()
        except Category.DoesNotExist:
            category = Category(id=qdata['cat_id'], name=qdata['cat_title'])
            category.save()
            category.questions.add(Question.objects.get(id=question.id))
            category.save()
        #     temp hack
        try:
            tag = Tag.objects.get(id=qdata['cat_id'])
            tag.questions.add(Question.objects.get(id=question.id))
            tag.save()
        except Tag.DoesNotExist:
            tag = Tag(id=qdata['cat_id'], text=qdata['cat_title'])
            tag.save()
            tag.questions.add(Question.objects.get(id=question.id))
            tag.save()
        update_counter(qdata)
        #     temp hack
        return qdata['cat_title']


def update_and_show_status(report, current_status):
    for k, v in current_status.iteritems():
        if report.get(k) is None:
            report[k] = v
        else:
            report[k] = report[k] + v
    sorted_by_value = sorted(current_status.items(), key=lambda kv: kv[1], reverse=True)
    length = min(10, len(sorted_by_value))
    text = ''
    for i in range(length):
        text += "{}: {}\n".format(sorted_by_value[i][1], sorted_by_value[i][0])
    print(text)
    return report


def import_from_api(page_from, amount):
    page_size = 1000
    pages = int(amount / page_size)
    last_page_size = amount % page_size
    html = '{}'
    report = {}
    print("importing from api {} pages".format(pages+1))
    try:
        if pages != 0:
            for i in range(pages + 1):
                current_status = {}
                if i == pages:
                    page_size = last_page_size
                try:
                    data = get_api_page(page_from, page_size)
                except Exception as e:
                    print("***** PROGRESS *****")
                    print("page: {}/{}".format(i + 1, pages + 1))
                    print("Error: {}".format(e.message))
                    page_from += page_size
                    continue
                if len(data) == 0:
                    print("Вопросы-то кончились!")
                    break
                for q in data:
                    result = save_question(parse_question(q))
                    if current_status.get(result) is None:
                        current_status[result] = 1
                    else:
                        current_status[result] += 1
                    page_from = int(q['id'])

                print("***** PROGRESS *****")
                print("page: {}/{}".format(i + 1, pages + 1))
                report = update_and_show_status(report, current_status)
                print("\n")
    finally:
        sorted_by_value = sorted(report.items(), key=lambda kv: kv[1], reverse=True)
        for (k, v) in sorted_by_value:
            html = html.format('{}  -  [{}] <br/> {}'.format(v, k, "{}"))
    return html


# 210800000-88111

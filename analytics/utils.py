# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
import pytz
import requests
from django.db.models import F

import math

import nltk
from nltk.stem.snowball import SnowballStemmer
import pymorphy2
from nltk.corpus import brown
from nltk.util import ngrams
from bs4 import BeautifulSoup
import string

from analytics.models import Question, Category, Tag, Counter, GlobalCounter
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

morph = pymorphy2.MorphAnalyzer()
stemmer = SnowballStemmer("russian")
stop_words = nltk.corpus.stopwords.words('russian')
# '' for python 2.7 only
stop_words.extend(
    ['хочу', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', 'нужно', 'вопрос', 'какие', 'подскажите', 'делать',
     'спасибо', 'как', 'помогите', 'пожалуйста', 'очень', 'почему', 'что', 'это', 'так', 'вот', 'быть', 'как', 'в', '—',
     'к', 'на', '`', '``', '.', '...', '..', u"''"])
stop_words = set(stop_words)
punctuation = set(string.punctuation)


def get_api_page(page_from, page_size):
    # url = 'https://otvet.mail.ru/api/v3/questions?limit={}&start_id={}'.format(page_size, page_from)
    url = 'https://otvet.mail.ru/api/v3/question/{}'.format(page_from)
    r = requests.get(url)
    if r.status_code == 200:
        # print(r.text)
        return r.json()
    else:
        raise Exception("server response code {} \n from url: {}".format(r.status_code, url))


def get_api(page_from):
    url = 'https://otvet.mail.ru/api/v3/question/{}'.format(page_from)
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


def update_counter(qdata, tags):
    for tag in tags:
        counter = Counter.objects.all().filter(category=Category.objects.get(id=qdata['cat_id']), tag=tag,
                                               datetime=qdata['date'].replace(minute=0, second=0)
                                                        + timedelta(hours=1))
        if not counter:
            counter = Counter(category=Category.objects.get(id=qdata['cat_id']), tag=tag,
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
        question = Question(text=qdata['text'].replace("\n", " "), created_at=qdata['date'], id=qdata['id'],
                            rating=qdata['rating'])
        question.save()
        tokens = tokenize_me(qdata['text'].replace("\n", " "))
        category = update_category(qdata['cat_title'], qdata['cat_id'], question.id)
        tags = []
        for token in tokens:
            tag = update_tag(tag_text=token, category_id=category.id, question_id=question.id, date=qdata['date'])
            tags.append(tag)
            update_global_counter(tag_id=tag.id, category_id=category.id)
        update_counter(qdata, tags)
        #     temp hack
        return qdata['cat_title']


def tokenize_me(input_text):
    soup = BeautifulSoup(input_text, features="html.parser")
    text = soup.get_text()
    tokens = nltk.word_tokenize(text.lower())
    tokens = [i for i in tokens if (i not in punctuation)]
    tokens = [t.strip(string.punctuation) for t in tokens if t not in stop_words]
    normalized_tokens = []
    for t in tokens:
        new_token = morph.parse(t)[0]
        if new_token.tag.POS is None:
            if str(new_token.tag) in ['UNKN', 'LATN']:
                normalized_tokens.append(new_token.normal_form)
        elif new_token.tag.POS in ['NOUN', 'VERB', 'INFN']:
            normalized_tokens.append(new_token.normal_form)
    tokens = set(normalized_tokens)
    return tokens


def update_tag(tag_text, category_id, question_id, date):
    try:
        tag = Tag.objects.get(text=tag_text)
        tag.questions.add(Question.objects.get(id=question_id))
        if tag.questions_count is None:
            tag.questions_count = 1
        else:
            tag.questions_count = F('questions_count') + 1
        if tag.created_at > date:
            tag.created_at = date
        tag.save()
    except Tag.DoesNotExist:
        tag = Tag(text=tag_text, questions_count=1, created_at=date)
        tag.save()
        tag.questions.add(Question.objects.get(id=question_id))
        tag.save()
    return tag


def update_category(category_title, category_id, question_id):
    try:
        category = Category.objects.get(id=category_id)
        category.questions.add(Question.objects.get(id=question_id))
        category.questions_count = F('questions_count') + 1
        category.save()
    except Category.DoesNotExist:
        category = Category(id=category_id, name=category_title)
        category.save()
        category.questions.add(Question.objects.get(id=question_id))
        category.questions_count = 1
        category.save()
    return category


def update_global_counter(tag_id, category_id):
    counter, created = GlobalCounter.objects.get_or_create(tag_id=tag_id, category_id=category_id,
                                                           defaults={'count': 1, 'local_idf': 0})
    if not created:
        counter.count = F('count') + 1
        counter.save()
    return counter


def update_local_idf():
    total_questions = Question.objects.all().count()
    global_counters = GlobalCounter.objects.all()
    for cnt in global_counters:
        # fixme
        if cnt.count is None:
            continue
        cnt.local_idf = math.log10(total_questions / cnt.count)
        cnt.save()
    return


def update_global_idf():
    total_questions = Question.objects.all().count()
    tags = Tag.objects.all()
    for tag in tags:
        # fixme
        if tag.questions_count is None:
            continue
        tag.global_idf = math.log10(total_questions / tag.questions_count)
        tag.save()
    return


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
        text += "{}: {}\n".format(sorted_by_value[i][1], sorted_by_value[i][0])
    return report


def import_from_api(page_from, amount):
    page_size = 1000
    pages = int(amount / page_size)
    last_page_size = amount % page_size
    html = '{}'
    report = {}
    print("importing from api {} pages".format(pages + 1))
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

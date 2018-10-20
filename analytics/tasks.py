# -*- coding: utf-8 -*-

from celery import shared_task
from datetime import datetime
from analytics.models import Question, Category
from .utils import get_api_page, parse_question, update_and_show_status, save_question
import os


@shared_task()
def test(arg):
    now = datetime.now().strftime("%b-%d_%H:%M:%S")
    print(now)



@shared_task()
def import_new():
    amount = 10000
    start_id = Question.objects.latest('id').id

    page_size = 1000
    pages = int(amount / page_size)
    if amount == 0:
        pages = 99999999
    report = {}
    result = []
    id_set = set()  # debug
    try:
        for i in range(pages + 1):
            current_status = {}
            try:
                data = get_api_page(start_id, page_size)
            except Exception as e:
                #                     start_id += page_size
                start_id += 1
                print(e)
                continue
            if len(data) == 0:
                print("Вопросы кончились!")
                break
            for q in data:
                if int(q['id']) not in id_set:
                    parsed = parse_question(q)
                    save_question(parsed)
                    result.append(parsed)

                    # analyse(parsed)

                    id_set.add(int(q['id']))
                start_id = int(q['id']) + 1
            report = update_and_show_status(report, current_status)
    except Exception as e:
        print(e)


def analyse():
    pass
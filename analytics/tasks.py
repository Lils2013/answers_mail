# -*- coding: utf-8 -*-

from celery import shared_task
from datetime import datetime
import os


@shared_task()
def test(arg):
    now = datetime.now().strftime("%b-%d_%H:%M:%S")
    print(now)



@shared_task()
def import_new():
    # все импорты моделей нужны именно здесь, внутри функции
    from analytics.models import Question, Category
    from .utils import get_api_page, parse_question, update_and_show_status, save_question

    start_id = Question.objects.latest('id').id

    page_size = 1000
    pages = 99999999
    report = {}
    result = []
    id_set = set()  # debug
    print("strarting new API import from id {}".format(start_id))
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
                start_id = int(q['id'])
            print("***** PROGRESS *****\npage: {}".format(i + 1))
            report = update_and_show_status(report, current_status)
    except Exception as e:
        print(e)


def analyse():
    pass
# -*- coding: utf-8 -*-
from contextlib import contextmanager

from celery import shared_task
from datetime import datetime
import os

from django.core.cache import cache
LOCK_EXPIRE = 60 * 10


@shared_task()
def test(arg):
    now = datetime.now().strftime("%b-%d_%H:%M:%S")
    print(now)


@shared_task()
def import_new():
    # все импорты моделей нужны именно здесь, внутри функции
    from analytics.models import Question, Category
    from .utils import parse_question, update_and_show_status, save_question, get_api, update_global_idf, update_local_idf

    lock_id = '{0}-lock'.format("import_new")
    with memcache_lock(lock_id, "import_new") as acquired:
        if acquired:
            start_id = 211100000
            #start_id = Question.objects.latest('id').id - 1
            pages = 1000
            report = {}
            result = []
            print("starting new API import from id {}".format(start_id))
            try:
                for i in range(pages + 1):
                    start_id += 1
                    current_status = {}
                    try:
                        data = get_api(start_id)
                    except Exception as e:
                        #                     start_id += page_size
                        print(e)
                        continue
                    if len(data) == 0:
                        print("Вопросы кончились!")
                        break
                    parsed = parse_question(data)
                    save_question(parsed)
                    result.append(parsed)
                    start_id = int(data['id'])
                    print("***** PROGRESS *****\npage: {}".format(i + 1))
                    report = update_and_show_status(report, current_status)
                update_global_idf()
                update_local_idf()
            except Exception as e:
                print(e)
            return
    print('Questions are already being imported by another worker')



def analyse():
    pass


@contextmanager
def memcache_lock(lock_id, oid):
    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if status:
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it
            cache.delete(lock_id)
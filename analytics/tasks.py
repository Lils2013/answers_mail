# -*- coding: utf-8 -*-
from contextlib import contextmanager

from celery import shared_task
from datetime import datetime

from django.core.cache import cache
# from django.test import RequestFactory

# from analytics import views

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
    import time

    lock_id = '{0}-lock'.format("import_new")
    with memcache_lock(lock_id, "import_new") as acquired:
        if acquired:
            # start_id = 211130000
            try:
                start_id = Question.objects.latest('id').id - 1
            except Exception as e:
                start_id = 210775613
                pass
            pages = 10000
            # start_id += pages + 1
            print("starting new API import from id {}".format(start_id))
            try:
                for i in range(pages):
                    start_id += 1
                    start = datetime.now()
                    try:
                        data = get_api(start_id)
                    except Exception as e:
                        print(e)
                        continue
                    if len(data) == 0:
                        print("Вопросы кончились!")
                        break
                    end1 = datetime.now()
                    print(end1 - start)
                    parsed = parse_question(data)
                    end2 = datetime.now()
                    print(end2 - end1)
                    save_question(parsed)
                    end3 = datetime.now()
                    print(end3 - end2)
                    print("loaded page: {}".format(i - 1))
                print('update_global_idf_start')
                # update_global_idf()
                print('update_local_idf_start')
                # update_local_idf()
            except Exception as e:
                print(e)
            return
    print('Questions are already being imported by another worker')



def analyse():
    pass


@contextmanager
def memcache_lock(lock_id, oid):
    # cache.add fails if the key already exists
    status = cache.add(lock_id, oid, None)
    try:
        yield status
    finally:
        # memcache delete is very slow, but we have to use it to take
        # advantage of using add() for atomic locking
        if status:
            print('RELEASED')
            # don't release the lock if we exceeded the timeout
            # to lessen the chance of releasing an expired lock
            # owned by someone else
            # also don't release the lock if we didn't acquire it
            cache.delete(lock_id)


#
# def cache_details(factory, tags, date, catid):
#     for t in tags:
#         views.get_questions(factory.get('/questions/?tags%5B%5D={}&date={}&catid={}'.format(t['id'], date, catid)))
#         views.graphs(factory.get('/questions/?tags%5B%5D={}&date={}&catid={}'.format(t['id'], date, catid)))
#
#
# def init_requests_cache():
#     print("Init frequent requests cache")
#     now = datetime.now()
#     factory = RequestFactory()
#     tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-d&catid=')).data
#     cache_details(factory, tags, 'now+1-d', '')
#     tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+7-d&catid=')).data
#     # cache_details(factory, tags, 'now+7-d', '')
#     tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-m&catid=')).data
#     # cache_details(factory, tags, 'now+1-m', '')
#     tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-y&catid=')).data
#     # cache_details(factory, tags, 'now+1-y', '')
#
#     cats = views.categories(factory.get('/categories/')).data
#     for cat in cats:
#         cat_id = cat['id']
#         print("caching category {}".format(cat_id))
#         tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-d&catid={}'.format(cat_id))).data
#         # cache_details(factory, tags, 'now+1-d', cat_id)
#
#         tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+7-d&catid={}'.format(cat_id))).data
#         # cache_details(factory, tags, 'now+7-d', cat_id)
#
#         tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-m&catid={}'.format(cat_id))).data
#         # cache_details(factory, tags, 'now+1-m', cat_id)
#
#         tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-y&catid={}'.format(cat_id))).data
#         # cache_details(factory, tags, 'now+1-y', cat_id)
#     print("full cache time: {}".format(datetime.now() - now))
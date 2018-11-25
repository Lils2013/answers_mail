# -*- coding: utf-8 -*-
import re
from datetime import datetime, timedelta

import pytz
from django.core.management.base import BaseCommand

# Create your views here.
from analytics.utils import save_question, tokenize_me
from analytics.models import Question, Category, Tag, Counter

# всего в дампе 3287939 вопросов
category_m = {}  # {id: {name: str, questions_count: int}}
question_m = {}  # {id: {text: str, created_at: str, category: int, rating: str}}
tag_m = {}  # {text: {id:int, questions:[id1, id2, ...], created_at: str} }
counter_m = {}  # {category_id: {tag_text:{ datetime:{count: int} } }

# минимальное количество вопросов, которые должны ссылаться на тег, чтобы он был сохранён в бд
tag_min_frequency = 3


def ram_save_question(qdata):
    try:
        q = Question.objects.get(id=qdata['id'])
        return
    except Question.DoesNotExist:
        q = question_m.get(qdata['id'])
        if q is None:
            q = {"text": qdata['text'].replace("\n", " "),
                 "created_at": qdata['date'],
                 "id": qdata['id'],
                 "category": qdata['cat_id'],
                 "rating": qdata['rating']}
            question_m[qdata['id']] = q
        else:
            return

        category = category_m.get(qdata['cat_id'])
        if category is None:
            category = {"name": qdata['cat_title'], "questions_count": 1}
            category_m[qdata['cat_id']] = category
        else:
            category["questions_count"] += 1

        tokens = tokenize_me(qdata['text'].replace("\n", " "))
        for token in tokens:
            tag = tag_m.get(token)
            if tag is None:
                tag = {"questions": [qdata['id']], "questions_count": 1, "created_at": qdata['date']}
                tag_m[token] = tag
            else:
                tag["questions"].append(qdata['id'])
                tag["questions_count"] += 1

            cat_cnt = counter_m.get(qdata['cat_id'])
            if cat_cnt is None:
                cat_cnt = {}
                counter_m[qdata['cat_id']] = cat_cnt

            tag_cnt = cat_cnt.get(token)
            if tag_cnt is None:
                tag_cnt = {}
                cat_cnt[token] = tag_cnt

            cnt = tag_cnt.get(qdata['date'].replace(minute=0, second=0) + timedelta(hours=1))
            if cnt is None:
                cnt = {"count": 1}
                tag_cnt[qdata['date'].replace(minute=0, second=0) + timedelta(hours=1)] = cnt
            else:
                cnt["count"] += 1


def ram_to_db():
    print("writing to DB:")
    start_t = datetime.now()
    existing_categories = Category.objects.filter(id__in=category_m.keys()).values_list('id', flat=True)
    for iid, data in category_m.iteritems():
        if iid in existing_categories:
            category = Category.objects.get(id=iid)
            category.questions_count += data["questions_count"]
            category.save()
        else:
            category = Category(id=iid, name=data["name"], questions_count=data["questions_count"])
            category.save()

    print("\tcategories time: {}".format(datetime.now() - start_t))
    start_t = datetime.now()

    existing_questions = Question.objects.filter(id__in=question_m.keys()).values_list('id', flat=True)
    for iid, data in question_m.iteritems():
        if iid in existing_questions:
            continue
        else:
            question = Question(text=data['text'], created_at=data['created_at'], id=iid, rating=data['rating'],
                                category_id=data["category"])
            question.save()

    print("\tquestions time: {}".format(datetime.now() - start_t))
    start_t = datetime.now()

    for iid, data in tag_m.iteritems():
        if len(data["questions"]) < tag_min_frequency:
            continue
        tags = Tag.objects.filter(text__exact=iid[:150])
        if len(tags) > 0:
            tag = tags[0]
            tag.questions_count += data["questions_count"]
            tag.questions.add(*data["questions"])
            tag.save()
            data["id"] = tag.id
        else:
            tag = Tag(text=iid[:150], questions_count=data["questions_count"], created_at=data["created_at"])
            tag.save()
            tag.questions.add(*data["questions"])
            tag.save()
            data["id"] = tag.id

    print("\ttags time: {}".format(datetime.now() - start_t))
    start_t = datetime.now()

    # {category_id: {tag_id: {datetime: {count: int}}}
    for category_id, d1 in counter_m.iteritems():
        for tag_text, d2 in d1.iteritems():
            for date_time, cnt in d2.iteritems():
                if len(tag_m[tag_text]["questions"]) < tag_min_frequency:
                    continue

                counter = Counter.objects.all().filter(category_id=category_id, tag_id=tag_m[tag_text]["id"],
                                                       datetime=date_time)
                if not counter:
                    counter = Counter(category_id=category_id, tag_id=tag_m[tag_text]["id"], datetime=date_time,
                                      count=cnt["count"])
                    counter.save()
                else:
                    counter = counter[0]
                    counter.count += cnt["count"]
                    counter.save()
    print("\tcounters time: {}".format(datetime.now() - start_t))


def print_ram_stats():
    junk_tags1 = []
    junk_tags5 = []
    junk_tags10 = []
    profit_tags10 = []

    # tag_m = {text: {id:int, questions:[id1, id2, ...], created_at: str} }
    for tag_id, data in tag_m.iteritems():
        if len(data["questions"]) == 1:
            junk_tags1.append(tag_id)
        if len(data["questions"]) < 5:
            junk_tags5.append(tag_id)
        if len(data["questions"]) < 10:
            junk_tags10.append(tag_id)
        if len(data["questions"]) >= 10:
            profit_tags10.append(tag_id)

    print("Вопросов в RAM: {}".format(len(question_m)))
    print("тегов: {}".format(len(tag_m)))
    print("Из них:")
    print("\t questions ==  1: {} ({:.1f}%)".format(len(junk_tags1), 100 * len(junk_tags1) / float(len(tag_m))))
    print("\t questions <   5: {} ({:.1f}%)".format(len(junk_tags5), 100 * len(junk_tags5) / float(len(tag_m))))
    print("\t questions <  10: {} ({:.1f}%)".format(len(junk_tags10), 100 * len(junk_tags10) / float(len(tag_m))))
    print("\t questions >= 10: {} ({:.1f}%)".format(len(profit_tags10), 100 * len(profit_tags10) / float(len(tag_m))))


def print_progress_and_savedb(last_date, start_t, start_full, start_id, i):
    print("\nдата: {}".format(last_date))
    print("Вопросов в RAM: {}".format(len(question_m)))
    ram_time = datetime.now() - start_t
    print("время обработки в RAM: {}".format(ram_time))
    start_t = datetime.now()
    ram_to_db()
    db_time = datetime.now() - start_t
    print("время сохранения в бд: {}".format(db_time))
    start_t = datetime.now()
    print("итоговое время обработки: {}".format(ram_time + db_time))
    print("время с запуска: {}".format(datetime.now() - start_full))
    print("обработано вопросов с запуска: {}".format(i - start_id))
    print("скорость: {:.1f} вопросов в секунду".format((i - start_id) / (datetime.now() - start_full).total_seconds()))


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("otvet-queastions-2018-2.txt") as tsvfile:
            start_full = datetime.now()
            start_t = datetime.now()
            last_date = datetime.now()

            start_id = 0
            for i, line in enumerate(tsvfile):
                if i < start_id:
                    continue
                line_data = re.split('\t', line)
                question_text = line_data[9].rstrip().lstrip()
                if (len(line_data) == 11):
                    question_text += ' '.encode('utf-8') + line_data[10].rstrip().lstrip()
                created_at = datetime.strptime(line_data[1], "%Y-%m-%d %H:%M:%S")
                timezone = pytz.timezone("Europe/Moscow")
                created_at = timezone.localize(created_at)
                cat_title = line_data[6]
                cat_id = int(line_data[5])
                qid = int(line_data[0])
                qdata = dict(id=qid, text=question_text, date=created_at, cat_title=cat_title, cat_id=cat_id,
                             rating=int(line_data[2]))

                # save_question(qdata)
                ram_save_question(qdata)

                curr_date = qdata['date'].replace(hour=0, minute=0, second=0)

                if i == start_id:
                    print("start date: {}".format(created_at))
                    last_date = curr_date

                if last_date - curr_date == timedelta(days=1):
                # if i != 0 and i % 1000 == 0:
                    print_progress_and_savedb(last_date,start_t,start_full, start_id, i)
                    last_date = curr_date
                    start_t = datetime.now()
                    category_m.clear()
                    question_m.clear()
                    tag_m.clear()
                    counter_m.clear()

        self.stdout.write(self.style.SUCCESS('Successfully loaded the dump'))

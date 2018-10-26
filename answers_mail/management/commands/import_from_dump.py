import re
from datetime import datetime

import pytz
from django.core.management.base import BaseCommand

# Create your views here.
from analytics.utils import save_question


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("otvet-queastions-2018-2.txt") as tsvfile:
            for line in tsvfile:
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
                save_question(qdata)
                # question = Question(text=question_text, rating=int(line_data[2]), created_at=created_at,
                #                     id=int(line_data[0]))
                # question.save()
                # try:
                #     tag = Tag.objects.get(id=int(line_data[5]))
                #     tag.questions.add(Question.objects.get(id=question.id))
                #     tag.save()
                # except Tag.DoesNotExist:
                #     tag = Tag(id=int(line_data[5]), text=line_data[6])
                #     tag.save()
                #     tag.questions.add(Question.objects.get(id=question.id))
                #     tag.save()
                # # try:
                # #     tag = Tag.objects.get(id=int(line_data[7]))
                # #     tag.questions.add(Question.objects.get(id=question.id))
                # #     tag.save()
                # # except Tag.DoesNotExist:
                # #     tag = Tag(id=int(line_data[7]), text=line_data[8])
                # #     tag.save()
                # #     tag.questions.add(Question.objects.get(id=question.id))
                # #     tag.save()
                # try:
                #     category = Category.objects.get(id=int(line_data[5]))
                #     category.questions.add(Question.objects.get(id=question.id))
                #     category.save()
                # except Category.DoesNotExist:
                #     category = Category(id=int(line_data[5]), name=line_data[6])
                #     category.save()
                #     category.questions.add(Question.objects.get(id=question.id))
                #     category.save()
                # # try:
                # #     category = Category.objects.get(id=int(line_data[7]))
                # #     category.questions_parent.add(Question.objects.get(id=question.id))
                # #     category.save()
                # # except Category.DoesNotExist:
                # #     category = Category(id=int(line_data[7]), name=line_data[8])
                # #     category.save()
                # #     category.questions_parent.add(Question.objects.get(id=question.id))
                # #     category.save()
                # # try:
                # counter = Counter.objects.all().filter(category=category, tag=tag,
                #                                        datetime=created_at.replace(minute=0, second=0)
                #                                                 + timedelta(hours=1))
                # if not counter:
                #     counter = Counter(category=category, tag=tag,
                #                       datetime=created_at.replace(minute=0, second=0) + timedelta(hours=1), count=1)
                #     counter.save()
                # else:
                #     counter = counter[0]
                #     counter.count = F('count') + 1
                #     counter.save()
        self.stdout.write(self.style.SUCCESS('Successfully loaded the dump'))

# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from django.http import HttpResponse
import datetime
import requests
import json
# Create your views here.


def import_data(request, page_from = -1, page_to = -1):
    now = datetime.datetime.now()
    html = "<html><body>It is now {}.</b> from: {} </b> to: {}</body></html>".format(now, page_from, page_to)
    if (page_to == -1):
        r = requests.get('https://otvet.mail.ru/api/v2/question?qid={}'.format(page_from))
        if (r.status_code == 200):
            # data = json.loads('{"lat":444, "lon":555}')
            html = "<html><body> {} </body></html>".format(r.text)

            # r.headers['content-type']
        # 'application/json; charset=utf8'
        #  r.encoding
        # 'utf-8'
        # >> > r.text
        # u'{"type":"User"...'
        # >> > r.json()
        # {u'private_gists': 419, u'total_private_repos': 77, ...}
    return HttpResponse(html)
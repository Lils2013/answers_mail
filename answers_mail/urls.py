"""answers_mail URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from datetime import datetime
from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic import TemplateView
from django.test.client import RequestFactory

from analytics import views
from .routers import router

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include(router.urls)),
    url(r'^answers/', TemplateView.as_view(template_name='index.html')),
    # url(r'^import/$', import_from_api_view),
    # url(r'^import_from_dump/$', import_from_dump),
    # url(r'^import/(?P<page_from>\d+)$', import_from_api_view),
    # url(r'^import/(?P<page_from>\d+)-(?P<amount>\d+)$', import_from_api_view),
    url(r'^questions/(?P<pk>[0-9]+)$', views.tag_detail),
    url(r'^questions/$', views.get_questions),
    url(r'^tags/$', views.tags),
    # url(r'^tags/(?P<pk>[0-9]+)$', views.tags_with_category),
    # url(r'^tags/(?P<pk>[0-9]+)/(?P<sort_type>[\w\-]+)$', views.tags_with_category),
    # url(r'^tags/(?P<sort_type>[\w\-]+)$$', views.tags),
    url(r'^categories/$', views.categories),
    # url(r'^graph/(?P<pk>[0-9]+)/(?P<time_interval>[\-0-9a-zA-Z]+)$', views.graph),
    url(r'^graph/$', views.graphs),
]


def cache_details(factory, tags, date, catid):
    for t in tags:
        views.get_questions(factory.get('/questions/?tags%5B%5D={}&date={}&catid={}'.format(t['id'], date, catid)))
        views.graphs(factory.get('/questions/?tags%5B%5D={}&date={}&catid={}'.format(t['id'], date, catid)))


def init_requests_cache():
    print("Init frequent requests cache")
    now = datetime.now()
    factory = RequestFactory()
    tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-d&catid=')).data
    cache_details(factory, tags, 'now+1-d', '')
    tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+7-d&catid=')).data
    # cache_details(factory, tags, 'now+7-d', '')
    tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-m&catid=')).data
    # cache_details(factory, tags, 'now+1-m', '')
    tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-y&catid=')).data
    # cache_details(factory, tags, 'now+1-y', '')

    cats = views.categories(factory.get('/categories/')).data
    for cat in cats:
        cat_id = cat['id']
        print("caching category {}".format(cat_id))
        tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-d&catid={}'.format(cat_id))).data
        # cache_details(factory, tags, 'now+1-d', cat_id)

        tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+7-d&catid={}'.format(cat_id))).data
        # cache_details(factory, tags, 'now+7-d', cat_id)

        tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-m&catid={}'.format(cat_id))).data
        # cache_details(factory, tags, 'now+1-m', cat_id)

        tags = views.tags(factory.get('/tags/?sortType=qcount&date=now+1-y&catid={}'.format(cat_id))).data
        # cache_details(factory, tags, 'now+1-y', cat_id)
    print("full cache time: {}".format(datetime.now() - now))

init_requests_cache()

from django.shortcuts import redirect, render, Http404, HttpResponse
import json
import traceback
import urllib.request
import redis
import datetime
from django.conf import settings
from django.views import View


NIFTY_GAINER_SCRAPPER_URL = settings.SCRAPPER_URL.get('nifty_gainer', '')
NIFTY_LOSER_SCRAPPER_URL = settings.SCRAPPER_URL.get('nifty_loser', '')
POOL = redis.ConnectionPool(host='localhost', port=6380)

r_server = redis.StrictRedis(connection_pool=POOL, charset="utf-8", decode_responses=True)
API_TIME_DIFF = settings.API_TIME_DIFF



def nifty_data(gaining, losing):
    gainer_data_json = {}
    loser_data_json = {}
    header = {'Accept': '*/*',
              'Accept-Language': 'en-US,en;q=0.5',
              'Host': 'www1.nseindia.com',
              'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:28.0) Gecko/20100101 Firefox/28.0',
              'X-Requested-With': 'XMLHttpRequest'
              }
    if gaining:
        req = urllib.request.Request(NIFTY_GAINER_SCRAPPER_URL, headers=header)
        gainer_data_json = urllib.request.urlopen(req).read()
        gainer_data_json = json.loads(gainer_data_json)
        print(gainer_data_json)
    if losing:
        req = urllib.request.Request(NIFTY_LOSER_SCRAPPER_URL, headers=header)
        loser_data_json = urllib.request.urlopen(req).read()
        loser_data_json = json.loads(loser_data_json)
        print(loser_data_json)
    return gainer_data_json, loser_data_json



def redis_data():
    gained_key = 'gainer_data'
    loser_key = 'loser_data'
    gainer_data = r_server.get(gained_key)
    loser_data = r_server.get(loser_key)
    if not gainer_data:
        gainer_data, loser_data = nifty_data(True, False)
        r_server.set(gained_key, gainer_data)
    else:
        gainer_data = eval(gainer_data)
        server_time = datetime.datetime.strptime(
            gainer_data.get('time'), '%b %d, %Y %H:%M:%S')
        current_system_time = datetime.datetime.now()
        adjusted_time = current_system_time - datetime.timedelta(minutes=5)
        if adjusted_time > server_time:
            gainer_data, loser_data = nifty_data(True, False)
            r_server.set(gained_key, gainer_data)
    if not loser_data:
        gainer_data_dummy, loser_data = nifty_data(False, True)
        r_server.set(loser_key, loser_data)
    else:
        loser_data = eval(loser_data)
        server_time = datetime.datetime.strptime(
            loser_data.get('time'), '%b %d, %Y %H:%M:%S')
        current_system_time = datetime.datetime.now()
        adjusted_time = current_system_time - datetime.timedelta(minutes=5)
        if adjusted_time > server_time:
            gainer_data_dummy, loser_data = nifty_data(False, True)
            r_server.set(loser_key, loser_data)
    return gainer_data, loser_data


class GetStockData(View):
    def get(self, request):
        gainer_data_json, loser_data_json = redis_data()
        table_heading = list(gainer_data_json['data'][0].keys())
        return render(request, 'index.html', {'headings': table_heading,
            'gainer_data': gainer_data_json['data'],
                                              'loser_data': loser_data_json['data']})



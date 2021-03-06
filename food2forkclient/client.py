# -*- coding: utf-8 -*-
import json
import os
import socket
import sys
try:
    import httplib
except ImportError:
    import http.client as httplib
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode
try:
    from urllib2 import HTTPError, URLError
except ImportError:
    from urllib.error import HTTPError, URLError
try:
    import urllib2
except ImportError:
    import urllib.request as urllib2
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse


try:
    API_KEY = os.environ['API_KEY']
except KeyError:
    API_KEY = None
    sys.stderr.write('Please set os.environ["API_KEY"] = yourapikey, '
                     'or pass api_key param in Food2ForkClient')


def error_handler(fn):
    def request_wrapper(self, *args, **kwargs):
        """
        add repeat requests for timeout
        """
        try:
            response = fn(self, *args, **kwargs)
        except HTTPError as e:
            raise Food2ForkHTTPError(e)
        except URLError as e:
            if isinstance(e.reason, socket.timeout):
                msg = '{0}'.format(e.reason)
                raise Food2ForkSocketError(msg)
            else:
                msg = 'URLError - {0}'.format(e.reason)
                raise Food2ForkClientException(msg)
        except httplib.HTTPException:
            raise Food2ForkHTTPException('HTTPException')
        except Exception:
            import traceback
            msg = 'Exception - {0}'.format(traceback.format_exc())
            raise Food2ForkClientException(msg)
        if response.code != 200:
            raise Food2ForkClientException('Problem with Food2Fork API')
        return response
    return request_wrapper


def user_error_handler(fn):
    def response_wrapper(self, response):
        python_response = fn(self, response)
        parsed_url = urlparse.urlparse(response.url)
        path = parsed_url.path
        error = python_response.get('error', '')
        if error:
            raise Food2ForkClientException('API call limit exceded')
        elif path == '/api/search/':
            results = python_response.get('recipes', '')
            if not results:
                raise Food2ForkClientException('Page # does not exist')
        elif path == '/api/get/':
            results = python_response.get('recipe', '')
            if not results:
                raise Food2ForkClientException('Recipe id does not exist')
        return results
    return response_wrapper


class Food2ForkClientException(Exception):
    pass


class Food2ForkHTTPException(Exception):
    pass


class Food2ForkHTTPError(Exception):

    def __init__(self, value):
        error = value
        if error.code == 403:
            self.code = 403
            self.value = '403 Check API key'
        elif error.code == 500:
            self.code = 500
            self.value = '500 Invalid search params?'
        else:
            self.value = '{0} {1}'.format(error.code, error.reason)

    def __str__(self):
        return repr(self.value)


class Food2ForkSocketError(Exception):

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class Food2ForkClient(object):
    URL_API = 'http://food2fork.com/api'
    URL_SEARCH = URL_API + '/search/?'
    URL_GET = URL_API + '/get/?'
    HEADERS = {"Content-Type": "application/json"}

    def __init__(self, api_key=API_KEY, timeout=None):
        self.api_key = api_key
        self.timeout = timeout
        msg = ('Must pass api_key, or set '
               'os.environ["API_KEY"] = yourapikey')
        assert(api_key is not None), msg

    def search(self, q=None, page=1, count=30):
        """
        kwargs:
        q: search_query
        page: used to get additional results
        count: number of results per search
        """
        assert(0 < count <= 30), 'max 30 results per call, min 1'
        query_params = [
            ('page', page),
            ('count', count)
        ]
        if q is not None:
            query_params.append(('q', q))
        query_params.append(('key', self.api_key))
        query_string = urlencode(query_params)
        url = self.URL_SEARCH + query_string
        response = self._request(url)
        return self._parse_json(response)

    def get(self, rid):
        """
        rid: rId (recipe_id) of recipe returned by search query
        """
        query_params = [('key', self.api_key), ('rId', rid)]
        query_string = urlencode(query_params)
        url = self.URL_GET + query_string
        response = self._request(url)
        return self._parse_json(response)

    @error_handler
    def _request(self, url):
        req = urllib2.Request(url)
        for key, value in self.HEADERS.items():
            req.add_header(key, value)
        response = urllib2.urlopen(req, timeout=self.timeout)
        return response

    @user_error_handler
    def _parse_json(self, response):
        #encoding = response.headers.get_content_charset()
        python_response = json.loads(response.read().decode('utf-8'))
        return python_response

#### 403 FORRBIDEN - bad key
#### 500 Internal Server Error page or count = None
####  {u'error': u'limit'}

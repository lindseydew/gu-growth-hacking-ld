import webapp2
import jinja2
import os
import json
import logging
import time
import collections

from urllib import quote, urlencode
from google.appengine.api import urlfetch
from google.appengine.api import memcache
from google.appengine.api import taskqueue

from google.appengine.ext import deferred

import headers
import ophan
import content_api
import formats

import json
import urlparse
from urlparse import urlparse, parse_qs

jinja_environment = jinja2.Environment(
	loader=jinja2.FileSystemLoader(os.path.join(os.path.dirname(__file__), "templates")))

TEN_MINUTES = 10 * 60
OPHAN_PARAMS = ['country', 'section', 'host', 'platform', 'uatype', 'uafamily', 'campaign', 'referrer']

def fresh(current_seconds):
	return (time.time() - current_seconds) < TEN_MINUTES

def resolve_content(url):
	params = {'show-fields' : 'headline,thumbnail,trailText'}

	result = content_api.read(content_api.content_id(url), params)

	if result:
		data = json.loads(result)
		return data.get('response', {}).get('content', {})
	return None

def read_ophan(query_str=None):

    client = memcache.Client()

    last_read = client.get(query_str + ".epoch_seconds")

    if last_read and fresh(last_read): return
    ophan_json = ophan.popular(query_str)

    if not ophan_json:
        raise deferred.PermanentTaskFailure()

    ophan_data = json.loads(ophan_json)

    resolved_stories = [resolve_content(entry['url']) for entry in ophan_data]

    resolved_stories = [story for story in resolved_stories if not story == None]

    client = memcache.Client()

    base_key = 'all'

    if query_str: base_key = query_str
    logging.info(base_key)
    if len(resolved_stories) > 0:
        client.set(base_key, json.dumps(resolved_stories))
        client.set(base_key + '.epoch_seconds', time.time())

    logging.info("Updated data for section %s; listing %d stories" % (query_str, len(resolved_stories)))

def refresh_data(query_str):
	deferred.defer(read_ophan, query_str)

def make_key(query_str):
    query_dict = parse_qs(query_str)
    query_dict_od = collections.OrderedDict(sorted(query_dict.items()))
    str = ""
    for k, vs in query_dict_od.iteritems():
        if k in OPHAN_PARAMS:
            if len(vs) > 0:
                str = str + k + "=" + vs.pop() + "&"
                for v in vs:
                    str = str + "," + v + "&"
    return str[:-1]

class MainPage(webapp2.RequestHandler):
	def get(self):
		template = jinja_environment.get_template('index.html')
		
		template_values = {}

		self.response.out.write(template.render(template_values))

class MostViewed(webapp2.RequestHandler):
	def get(self):
            client = memcache.Client()
            query_str = self.request.query_string
            key = 'all'
            if query_str:
                key = make_key(query_str)

            ophan_json = client.get(key)
            if not ophan_json:
                refresh_data(key)
                ophan_json = "[]"

            last_read = client.get(key + ".epoch_seconds")
            logging.info(key)
            if last_read and not fresh(last_read):
                refresh_data(key)

            headers.json(self.response)
            headers.set_cache_headers(self.response, 60)
            headers.set_cors_headers(self.response)
            self.response.out.write(formats.jsonp(self.request, ophan_json))

class EditorsPicks(webapp2.RequestHandler):
    def get(self, edition):

        client = memcache.Client()
        key = edition
        content_json = client.get(key)
        logging.info("content from memcache with key %s" % key)

        if not content_json:
            logging.info("no content found in memcache")
            content_json = content_api.editors_picks(edition)

        editors_picks = (json.loads(content_json)).get('response').get('editorsPicks')
        
        if editors_picks is None:
            logging.warning("could not parse editorsPicks from the response body")
            return_json = content_json   
        else:
            return_json = json.dumps(editors_picks)   

        headers.json(self.response)
        headers.set_cache_headers(self.response, 60)
        headers.set_cors_headers(self.response)
        self.response.out.write(formats.jsonp(self.request, return_json))


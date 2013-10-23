from google.appengine.api.urlfetch import fetch
from google.appengine.api import memcache
from google.appengine.ext import ndb

import logging
import urllib
import re
from models import Configuration

client = memcache.Client()

FIFTEEN_MINUTES = 15 * 60


def popular(query_str):
#	results = Configuration.query(Configuration.key == "OPHAN_API_KEY")
#	if not results.iter().has_next():
#		return None

#	ophan_api_key = results.iter().next().value
    ophan_api_key = "lindsey"
    logging.info(ophan_api_key)

    most_read_url = "http://api.ophan.co.uk/api/mostread"

    params = {'age' : FIFTEEN_MINUTES,
        'api-key' : ophan_api_key}

    append_url = None

    if query_str is not None:

        append_url = "&" + query_str.replace("&callback=social", "")

    most_read_url = most_read_url + "?" + urllib.urlencode(params) + append_url

    logging.info(most_read_url)

    result = fetch(most_read_url)

    if result.status_code == 200:
        logging.info(result.content)
        return result.content

    logging.error("Ophan read failed with status code %d" % result.status_code)
    return None
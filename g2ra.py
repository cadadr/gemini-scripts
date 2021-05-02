#!/usr/bin/env python3
# g2ra.py --- gemini to RSS or Atom proxy

# Copyright (c) 2021 Göktuğ Kayaalp

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# requirements: flask, ignition-gemini

# TODO
# - XXX validate ttl and author (and other stuff more stricter)
# - TODO deal with redirects

import ignition
import io
import sys
import xml.etree.ElementTree as ET

from datetime import datetime, timezone
from flask import Flask, abort, make_response, request, url_for
from urllib.parse import urljoin, urlparse, urlunparse
from wsgiref.handlers import CGIHandler
from xml.dom import minidom


TTL_DEFAULT = "1800"
AUTHOR_DEFAULT = "Unknown Author Jr."
MAX_REDIRECTS = 1


def parse(string):
    lines = string.split("\n")
    feed_title, lines = accept(expect_title, lines)
    maybe_subtitle, lines = accept(expect_nonempty, lines)
    feed_subtitle_maybe, lines = accept_one(
            expect_subtitle, [maybe_subtitle or "", *lines])
    # collect links
    links = []
    while True:
        feed_item_maybe, lines = accept(expect_feed_item, lines)
        if feed_item_maybe:
            links.append(feed_item_maybe)
        if len(lines) == 0:
            break
    if len(links) > 0:
        sorted_links = sorted(links, key=lambda x: x['date'], reverse=True)
        return {
            'title': feed_title,
            'subtitle': feed_subtitle_maybe,
            'updated': sorted_links[0]['date'],
            'links': links,
            'lines_remaining': lines
        }


def accept(fun, lines):
    if len(lines) == 0:
        return (None, [])
    found = fun(lines[0])
    if found is not None:
        return (found, lines[1:])
    return accept(fun, lines[1:])


def accept_one(fun, lines):
    if len(lines) == 0:
        return (None, [])
    found = fun(lines[0])
    if found is not None:
        return (found, lines[1:])
    return (None, lines)


def expect_title(line):
    if line.startswith('# '):
        return line[2:]


def expect_nonempty(line):
    if line.strip() != '':
        return line


def expect_subtitle(line):
    if line.startswith('## '):
        return line[3:]


def expect_feed_item(line):
    if not line.startswith('=> '):
        return None
    try:
        _, link, description = line.split(maxsplit=2)
        date_string_maybe, rest = description.split(maxsplit=1)
        date = datetime.strptime(date_string_maybe,
                "%Y-%m-%d").astimezone(tz=timezone.utc)
        return {
            'link': link,
            'description': rest,
            'date': date
        }
    except ValueError:      #probably malformed link, but strptime
                            #raises ValueError if format does not
                            #match.
        return None


def convert(url, type_, content, **kwargs):
    data = parse(content)
    if data is None:
        return None
    data.update(kwargs)
    if type_ == 'atom':
        return atom_feed(url, data)
    if type_ == 'rss':
        return rss_feed(url, data)

def xml_stringify(element):
    # This is disgusting but it works and I already sank too much time
    # into converting fucking XML to a bloody string so fuck it.
    xmlstr = ET.tostring(element, encoding="unicode")
    pretty = minidom.parseString(xmlstr).toprettyxml(encoding="UTF-8")
    return pretty


def atom_feed(url, data):
    feed = ET.Element('feed', xmlns='http://www.w3.org/2005/Atom')
    title = ET.SubElement(feed, "title")
    title.text = data['title']
    link = ET.SubElement(feed, "link", href=url, rel="self")
    updated = ET.SubElement(feed, "updated")
    updated.text = data['updated'].isoformat()
    id_ = ET.SubElement(feed, "id")
    id_.text = url
    subtitle_maybe = data.get('subtitle')
    if subtitle_maybe is not None:
        subtitle = ET.SubElement(feed, 'subtitle')
        subtitle.text = subtitle_maybe

    for link in data['links']:
        entry = ET.SubElement(feed, 'entry')
        title = ET.SubElement(entry, "title")
        title.text = link['description']
        updated = ET.SubElement(entry, "updated")
        updated.text = link['date'].isoformat()
        href = urlparse(link['link'])
        url_ = urlparse(url)
        if href.netloc == '':
            # HACK because fuck Python and it's batteries
            href = href._replace(netloc=url_.netloc)
            href = href._replace(netloc=url_.netloc)
            path = urljoin(url_.path, href.path)
            href = href._replace(path=path)
            href = href._replace(scheme='gemini')
        href = urlunparse(href)
        link_ = ET.SubElement(entry, "link", href=href, rel="alternate")
        entry_id = ET.SubElement(entry, "id")
        entry_id.text = href
        author = ET.SubElement(entry, "author")
        author_name = ET.SubElement(author, "name")
        author_name.text = data['author']

    return xml_stringify(feed)


# Adapted from http://johnbokma.com/blog/2019/10/09/rfc-822-and-rfc-3339-dates-in-python.html
def rss_date(date_obj):
    # XXX This is weird but I will think about it later.
    end_of_day = datetime.strptime(
            f'{date_obj.strftime("%F")} 00:00:00',
            '%Y-%m-%d %H:%M:%S').astimezone()
    ctime = date_obj.ctime()
    return (f'{ctime[0:3]}, {end_of_day.day:02d} {ctime[4:7]}'
                + end_of_day.strftime(' %Y %H:%M:%S %z'))


# Adapted copy of `atom_feed'.
def rss_feed(url, data):
    feed = ET.Element('rss', version='2.0', attrib={
        "xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = ET.SubElement(feed, "channel")
    title = ET.SubElement(channel, "title")
    title.text = data['title']
    link = ET.SubElement(channel, "link")
    link.text = url
    atom_link = ET.SubElement(channel,
            "atom:link", rel="self", href=url)
    pub_date = rss_date(data['updated'])
    pubDate = ET.SubElement(channel, "pubDate")
    pubDate.text = pub_date
    lastBuildDate = ET.SubElement(channel, "lastBuildDate")
    lastBuildDate.text = pub_date
    param_ttl = data.get(ttl)
    ttl = ET.SubElement(channel, param_ttl)
    ttl.text = '1800' # TODO configable
    description_maybe = data.get('subtitle')
    if description_maybe is not None:
        description = ET.SubElement(channel, 'description')
        description.text = description_maybe

    for link in data['links']:
        entry = ET.SubElement(channel, 'item')
        title = ET.SubElement(entry, "title")
        title.text = link['description']
        pubDate = ET.SubElement(entry, "pubDate")
        pubDate.text = rss_date(link['date'])
        href = urlparse(link['link'])
        url_ = urlparse(url)
        if href.netloc == '':
            href = href._replace(netloc=url_.netloc)
            href = href._replace(netloc=url_.netloc)
            path = urljoin(url_.path, href.path)
            href = href._replace(path=path)
            href = href._replace(scheme='gemini')
        href = urlunparse(href)
        link_ = ET.SubElement( entry, "link")
        link_.text = href
        # TODO: allow UUID for GUIDs?
        guid = ET.SubElement(entry, "guid", isPermaLink="true")
        guid.text = href

    return xml_stringify(feed)


app = Flask(__name__)


@app.route('/', methods=['GET'])
def main():
    param_url = request.args.get('url')
    if not param_url:
        abort(400) # HTTP 400 Bad Request
    param_type = request.args.get('type', 'atom').lower()
    gem_url = ignition.url(param_url)
    if param_type not in ['atom', 'rss']:
        raise Exception(f"unknown feed type: {param_type}")
    param_ttl = request.args.get("ttl", TTL_DEFAULT)
    param_author = request.args.get("author", AUTHOR_DEFAULT)
    response = ignition.request(str(gem_url), timeout=5.0)
    return reply(response, gem_url, param_type, param_ttl, param_author)


def reply(response, gem_url, param_type, param_ttl, param_author,
        num_redir=0):
    if isinstance(response, ignition.InputResponse):
        raise Exception("input")
    elif isinstance(response, ignition.SuccessResponse):
        xml = convert(gem_url, param_type, str(response),
                        ttl=param_ttl, author=param_author)
        if xml is None:
            abort(400)
        r = make_response(xml)
        r.headers['Content-Type'] = f'application/{param_type}+xml'
        return r
    elif isinstance(response, ignition.RedirectResponse):
        if True:
            abort(501) # HTTP 501 Not Implemented
        else:
            # or use flask.redirect?
            if num_redir > MAX_REDIRECTS:
                ...
            else:
                new_response = ...
                reply(new_response, gem_url, param_type, param_ttl,
                        param_author, num_redir + 1)
    elif isinstance(response, ignition.ClientCertRequiredResponse):
        abort(401) # HTTP 401 Unauthorized
    elif isinstance(response, ignition.TempFailureResponse):
        abort(503) # HTTP 503 Service Unavailable
    elif isinstance(response, ignition.PermFailureResponse):
        abort(502) # HTTP 502 Bad Gateway
    else:
        abort(500) # HTTP 500 Internal Server Error

if __name__ == '__main__':
    CGIHandler().run(app)



#!/usr/bin/env python3
# g2ra.py --- gemini to RSS or Atom proxy

# requirements: flask, ignition-gemini

# TODO
# - implement rss
# - deal with redirects
# - report errors better
#   - try couple redirects
#   - fail on empty feed?

import ignition
import io
import pprint
import sys
import xml.etree.ElementTree as ET

from datetime import datetime
from flask import Flask, request, url_for
from urllib.parse import urljoin, urlparse, urlunparse
from wsgiref.handlers import CGIHandler
from xml.dom import minidom

pp = pprint.PrettyPrinter(indent=4)

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
        date = datetime.strptime(date_string_maybe, "%Y-%m-%d")
        return {
            'link': link,
            'description': rest,
            'date': date
        }
    except ValueError:      #probably malformed link, but strptime
                            #raises ValueError if format does not
                            #match.
        return None


def convert(url, type_, content):
    data = parse(content)
    if type_ == 'atom':
        return atom_feed(url, data)
    if type_ == 'rss':
        return rss_feed(url, data)


def atom_feed(url, data):
    feed = ET.Element('feed', xmlns='http://www.w3.org/2005/Atom')
    title = ET.SubElement(feed, "title")
    title.text = data['title']
    link = ET.SubElement(feed, "link", href=url)
    updated = ET.SubElement(feed, "updated")
    updated.text = data['updated'].isoformat()
    id_ = ET.SubElement(feed, "id")
    id_.text = url

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
        link_ = ET.SubElement( entry, "link", href=href, rel="alternate")
        entry_id = ET.SubElement(entry, "id")
        entry_id.text = href

    # tree = ET.ElementTree(feed)

    # This is disgusting but it works and I already sank too much time
    # into converting fucking XML to a bloody string so fuck it.
    xmlstr = ET.tostring(feed, encoding="unicode")
    pretty = minidom.parseString(xmlstr).toprettyxml(encoding="UTF-8")
    return pretty


def rss_feed(url, data):
    ...


app = Flask(__name__)


@app.route('/', methods=['GET'])
def main():
    param_url = request.args.get('url')
    param_type = request.args.get('type', 'atom').lower()
    gem_url = ignition.url(param_url)
    if param_type not in ['atom', 'rss']:
        raise Exception(f"unknown feed type: {param_type}")
    response = ignition.request(str(gem_url), timeout=5.0)
    if isinstance(response, ignition.InputResponse):
        raise Exception("input")
    elif isinstance(response, ignition.SuccessResponse):
        # todo: accepts
        xml = convert(gem_url, param_type, str(response))
        return xml
    elif isinstance(response, ignition.RedirectResponse):
        # todo: try once
        ...
    # elif isinstance(response, ignition.ClientCertRequiredResponse):
    #     ...
    # elif isinstance(response, ignition.TempFailureResponse):
    #     ...
    # elif isinstance(response, ignition.PermFailureResponse):
    #     ...
    # elif isinstance(response, ignition.ErrorResponse):
    #     ...
    else:
        return f'''
            <h1>Error ({gem_url})</h1>
            <pre>{response}</pre>'''


if __name__ == '__main__':
    CGIHandler().run(app)



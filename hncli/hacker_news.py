# -*- coding: utf-8 -*-

# Copyright 2015 Donne Martin. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.

from __future__ import print_function
from __future__ import division

import os
import re
import urllib
from urlparse import urlparse
try:
    # Python 3
    import configparser
except ImportError:
    # Python 2
    import ConfigParser as configparser

import click
from html2text import HTML2Text
import requests

from .haxor.haxor import HackerNewsApi


class HackerNews(object):
    """Encapsulates Hacker News.

    Attributes:
        * COMMENT_INDENT: A string representing the indent amount for comments.
        * CONFIG: A string representing the config file name.
        * CONFIG_SECTION: A string representing the main config file section.
        * CONFIG_INDEX: A string representing the last index used.
        * hacker_news_api: An instance of HackerNews.
        * item_ids: A list containing the last set of ids the user has seen,
            which allows the user to quickly access an item with the
            gh view [#] [-u/--url] command.
        * TIP: A string that lets the user know about the hn view command.
        * URL_POST: A string that represents a Hacker News post minus the
            post id.
        * URL_W3_HTML_TEXT: A string that represents the w3 HTML to text
            converter service.
    """

    COMMENT_INDENT = '    '
    CONFIG = '.hncliconfig'
    CONFIG_SECTION = 'hncli'
    CONFIG_INDEX = 'item_ids'
    TIP = 'Tip: View the page or comments in your terminal with the ' \
          'following command:\n' \
          '    hn view [#] [-c/--comments]'
    URL_POST = 'https://news.ycombinator.com/item?id='
    URL_W3_HTML_TEXT = 'https://www.w3.org/services/html2txt?url='

    def __init__(self):
        """Initializes HackerNews.

        Args:
            * None.

        Returns:
            None.
        """
        self.hacker_news_api = HackerNewsApi()
        self.item_ids = []

    def _config(self, config_file_name):
        """Gets the config file path.

        Args:
            * config_file_name: A String that represents the config file name.

        Returns:
            A string that represents the hn config file path.
        """
        home = os.path.abspath(os.environ.get('HOME', ''))
        config_file_path = os.path.join(home, config_file_name)
        return config_file_path

    def print_comments(self, item, regex_query='', depth=0):
        """Recursively print comments and subcomments for the given item.

        Args:
            * item: An instance of haxor.Item.
            * regex_query: A string that specifies the regex query to match.
            * depth: The current recursion depth, used to indent the comment.

        Returns:
            None.
        """
        comment_ids = item.kids
        if item.text is not None:
            print_comment = True
            if regex_query and not self.regex_match(item, regex_query):
                print_comment = False
            if print_comment:
                self.print_formatted_comment(item, depth)
        if not comment_ids:
            return
        for comment_id in comment_ids:
            comment = self.hacker_news_api.get_item(comment_id)
            depth += 1
            self.print_comments(comment, regex_query=regex_query, depth=depth)
            depth -= 1

    def pretty_date_time(self, date_time):
        """Prints a pretty datetime similar to what's seen on Hacker News.

        Gets a datetime object or a int() Epoch timestamp and return a
        pretty string like 'an hour ago', 'Yesterday', '3 months ago',
        'just now', etc.

        Adapted from: http://stackoverflow.com/questions/1551382/user-friendly-time-format-in-python

        Args:
            * date_time: An instance of datetime.

        Returns:
            A string that represents the pretty datetime.
        """
        from datetime import datetime
        now = datetime.now()
        if type(date_time) is int:
            diff = now - datetime.fromtimestamp(date_time)
        elif isinstance(date_time, datetime):
            diff = now - date_time
        elif not date_time:
            diff = now - now
        second_diff = diff.seconds
        day_diff = diff.days
        if day_diff < 0:
            return ''
        if day_diff == 0:
            if second_diff < 10:
                return "just now"
            if second_diff < 60:
                return str(second_diff) + " seconds ago"
            if second_diff < 120:
                return "1 minute ago"
            if second_diff < 3600:
                return str(second_diff // 60) + " minutes ago"
            if second_diff < 7200:
                return "1 hour ago"
            if second_diff < 86400:
                return str(second_diff // 3600) + " hours ago"
        if day_diff == 1:
            return "Yesterday"
        if day_diff < 7:
            return str(day_diff) + " days ago"
        if day_diff < 31:
            return str(day_diff // 7) + " weeks ago"
        if day_diff < 365:
            return str(day_diff // 30) + " months ago"
        return str(day_diff // 365) + " years ago"

    def print_formatted_comment(self, item, depth):
        """Formats and prints a given item's comment.

        Args:
            * item: An instance of haxor.Item.
            * depth: The current recursion depth, used to indent the comment.

        Returns:
            None.
        """
        indent = self.COMMENT_INDENT * depth
        click.secho(
            '\n' + indent + item.by + ' - ' +
            str(self.pretty_date_time(item.submission_time)),
            fg='yellow')
        html_to_text = HTML2Text()
        html_to_text.body_width = 0
        markdown = html_to_text.handle(item.text)
        markdown = re.sub('\n\n', '\n\n' + indent, markdown)
        wrapped_markdown = click.wrap_text(
            text=markdown,
            initial_indent=indent,
            subsequent_indent=indent)
        click.echo(wrapped_markdown)

    def print_formatted_item(self, item, index):
        """Formats and prints an item.

        Args:
            * item: An instance of haxor.Item.
            * index: An int that specifies the index for the given item,
                used with the hn view [index] commend.

        Returns:
            None.
        """
        click.secho('  ' + str(index) + '. ',
                    nl=False,
                    fg='magenta')
        click.secho(item.title + '. ',
                    nl=False,
                    fg='blue')
        if item.url is not None:
            netloc = urlparse(item.url).netloc
            netloc = re.sub('www.', '', netloc)
            click.secho('(' + netloc + ')',
                        fg='magenta')
        else:
            click.echo('')
        click.secho('     ' + str(item.score) + ' points ',
                    nl=False,
                    fg='green')
        click.secho('by ' + item.by + ' ',
                    nl=False,
                    fg='yellow')
        click.secho(str(self.pretty_date_time(item.submission_time)) + ' ',
                    nl=False,
                    fg='cyan')
        num_comments = str(item.descendants) if item.descendants else '0'
        click.secho('| ' + num_comments + ' comments\n',
                    fg='green')
        self.item_ids.append(item.item_id)

    def print_items(self, message, item_ids):
        """Prints the items and headers with tabulate.

        Args:
            * message: A string to print out to the user before outputting
                the results.
            * item_ids: A collection of items to print as rows with tabulate.
                Can be a list or dictionary.

        Returns:
            None.
        """
        click.secho('\n' + message + '\n', fg='blue')
        index = 1
        for item_id in item_ids:
            item = self.hacker_news_api.get_item(item_id)
            if item.title:
                self.print_formatted_item(item, index)
                index += 1
        self.save_item_ids()
        click.secho(str(self.TIP), fg='blue')
        click.echo('')

    def print_url_contents(self, item):
        """Prints the contents of the given item's url.

        Converts the HTML to text using the w3 HTML to text service then
            displays the output in a pager.

        Args:
            * item: An instance of haxor.Item.

        Returns:
            None.
        """
        url_encoded = self.URL_W3_HTML_TEXT + urllib.quote(item.url, safe='')
        response = requests.get(url_encoded)
        click.echo_via_pager(response.text)

    def regex_match(self, item, regex_query):
        """Determines if there is a match with the given regex_query.

        Args:
            * item: An instance of haxor.Item.
            * regex_query: A string that specifies the regex query to match.

        Returns:
            A boolean that specifies whether there is a match.
        """
        match_time = re.search(
            regex_query,
            str(self.pretty_date_time(item.submission_time)))
        match_user = re.search(regex_query, item.by)
        match_text = re.search(regex_query, item.text)
        if not match_text and not match_user and not match_time:
            return False
        else:
            return True

    def save_item_ids(self):
        """Saves the current set of item ids to ~/.hncliconfig.

        Args:
            * None

        Returns:
            None.
        """
        config = self._config(self.CONFIG)
        parser = configparser.RawConfigParser()
        parser.add_section(self.CONFIG_SECTION)
        parser.set(self.CONFIG_SECTION, self.CONFIG_INDEX, self.item_ids)
        parser.write(open(config, 'w+'))

    def view(self, index, comments_query, comments):
        """Views the given index in a browser.

        Loads item ids from ~/.hncliconfig and stores them in self.item_ids.
        If url is True, opens a browser with the url based on the given index.
        Else, displays the post's comments.

        Args:
            * index: An int that specifies the index to open in a browser.
            * comments_query: A string that specifies the regex query to match.
            * comments: A boolean that determines whether to view the comments
                or a simplified version of the post url.

        Returns:
            None.
        """
        config = self._config(self.CONFIG)
        parser = configparser.RawConfigParser()
        try:
            parser.readfp(open(config))
            items_ids = parser.get(self.CONFIG_SECTION, self.CONFIG_INDEX)
            items_ids = items_ids.strip()
            excludes = ['[', ']', "'"]
            for exclude in excludes:
                items_ids = items_ids.replace(exclude, '')
            self.item_ids = items_ids.split(', ')
            item = self.hacker_news_api.get_item(self.item_ids[index-1])
            if comments:
                comments_url = self.URL_POST + str(item.item_id)
                click.secho('Fetching Comments from ' + comments_url, fg='blue')
                self.print_comments(item, regex_query=comments_query)
            else:
                click.secho('Opening ' + item.url + '...', fg='blue')
                self.print_url_contents(item)
        except Exception as e:
            click.secho('Error: ' + str(e), fg='red')

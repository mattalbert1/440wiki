"""
    Wiki core
    ~~~~~~~~~
"""
from collections import OrderedDict
from io import open
import os
import re

from flask import abort
from flask import url_for
import markdown
from pymongo import MongoClient


def clean_url(url):
    """
        Cleans the url and corrects various errors. Removes multiple
        spaces and all leading and trailing spaces. Changes spaces
        to underscores and makes all characters lowercase. Also
        takes care of Windows style folders use.

        :param str url: the url to clean


        :returns: the cleaned url
        :rtype: str
    """
    url = re.sub('[ ]{2,}', ' ', url).strip()
    url = url.lower().replace(' ', '_')
    url = url.replace('\\\\', '/').replace('\\', '/')
    return url


def wikilink(text, url_formatter=None):
    """
        Processes Wikilink syntax "[[Link]]" within the html body.
        This is intended to be run after content has been processed
        by markdown and is already HTML.

        :param str text: the html to highlight wiki links in.
        :param function url_formatter: which URL formatter to use,
            will by default use the flask url formatter

        Syntax:
            This accepts Wikilink syntax in the form of [[WikiLink]] or
            [[url/location|LinkName]]. Everything is referenced from the
            base location "/", therefore sub-pages need to use the
            [[page/subpage|Subpage]].

        :returns: the processed html
        :rtype: str
    """
    if url_formatter is None:
        url_formatter = url_for
    link_regex = re.compile(
        r"((?<!\<code\>)\[\[([^<].+?) \s*([|] \s* (.+?) \s*)?]])",
        re.X | re.U
    )
    for i in link_regex.findall(text):
        title = [i[-1] if i[-1] else i[1]][0]
        url = clean_url(i[1])
        html_url = u"<a href='{0}'>{1}</a>".format(
            url_formatter('wiki.display', url=url),
            title
        )
        text = re.sub(link_regex, html_url, text, count=1)
    return text


class Processor(object):
    """
        The processor handles the processing of file content into
        metadata and markdown and takes care of the rendering.

        It also offers some helper methods that can be used for various
        cases.
    """

    preprocessors = []
    postprocessors = [wikilink]

    def __init__(self, text):
        """
            Initialization of the processor.

            :param str text: the text to process
        """
        self.md = markdown.Markdown([
            'codehilite',
            'fenced_code',
            'meta',
            'tables'
        ])
        self.input = text
        self.markdown = None
        self.meta_raw = None

        self.pre = None
        self.html = None
        self.final = None
        self.meta = None

    def process_pre(self):
        """
            Content preprocessor.
        """
        current = self.input
        for processor in self.preprocessors:
            current = processor(current)
        self.pre = current

    def process_markdown(self):
        """
            Convert to HTML.
        """
        self.html = self.md.convert(self.pre)


    def split_raw(self):
        """
            Split text into raw meta and content.
        """
        self.meta_raw, self.markdown = self.pre.split('\n\n', 1)

    def process_meta(self):
        """
            Get metadata.

            .. warning:: Can only be called after :meth:`html` was
                called.
        """
        # the markdown meta plugin does not retain the order of the
        # entries, so we have to loop over the meta values a second
        # time to put them into a dictionary in the correct order
        self.meta = OrderedDict()
        for line in self.meta_raw.split('\n'):
            key = line.split(':', 1)[0]
            # markdown metadata always returns a list of lines, we will
            # reverse that here
            self.meta[key.lower()] = \
                '\n'.join(self.md.Meta[key.lower()])

    def process_post(self):
        """
            Content postprocessor.
        """
        current = self.html
        for processor in self.postprocessors:
            current = processor(current)
        self.final = current

    def process(self):
        """
            Runs the full suite of processing on the given text, all
            pre and post processing, markdown rendering and meta data
            handling.
        """
        self.process_pre()
        self.process_markdown()
        self.split_raw()
        self.process_meta()
        self.process_post()

        return self.final, self.markdown, self.meta


class Page(object):
    def __init__(self, url, db_page, new=False):
        #self.path = path
        self.url = url
        self.db_page = db_page
        self._meta = OrderedDict()
        if not new:
            self.load()
            self.render()

    def __repr__(self):
        return u"<Page: {}@{}>".format(self.url, self.path)

    def load(self):
        # with open(self.path, 'r', encoding='utf-8') as f:
        # self.content = f.read()
        if 'title' in self.db_page:
            self.content = 'title: ' + self.db_page['title'] + '\n'
        if 'tags' in self.db_page:
            self.content += 'tags: ' + self.db_page['tags'] + '\n\n'
        if 'body' in self.db_page:
            self.content += self.db_page['body']

    def render(self):
        processor = Processor(self.content)
        self._html, self.body, self._meta = processor.process()

    def save(self, update=True):
        # folder = os.path.dirname(self.path)
        # if not os.path.exists(folder):
        #     os.makedirs(folder)
        # with open(self.path, 'w', encoding='utf-8') as f:
        #     for key, value in self._meta.items():
        #         line = u'%s: %s\n' % (key, value)
        #         f.write(line)
        #     f.write(u'\n')
        #     f.write(self.body.replace(u'\r\n', u'\n'))
        my_db = Db()
        my_db.insert(self.url, self.title, self.tags, self.body)
        if update:
            self.load()
            self.render()

    @property
    def meta(self):
        return self._meta

    def __getitem__(self, name):
        return self._meta[name]

    def __setitem__(self, name, value):
        self._meta[name] = value

    @property
    def html(self):
        return self._html

    def __html__(self):
        return self.html

    @property
    def title(self):
        try:
            return self['title']
        except KeyError:
            return self.url

    @title.setter
    def title(self, value):
        self['title'] = value

    @property
    def tags(self):
        try:
            return self['tags']
        except KeyError:
            return ""

    @tags.setter
    def tags(self, value):
        self['tags'] = value


class Db(object):
    def get_page(self, url):
        try:
            client = MongoClient()
            db = client.wiki
            db_page = db.wiki.find_one({'url': url})
            if 'url' in db_page and url == db_page['url']:
                return Page(url, db_page)
            return None
        except Exception, e:
            print str(e)
        finally:
            client.close()

    def get_pages(self):
        pages = []
        try:
            client = MongoClient()
            db = client.wiki
            db_pages = db.wiki.find()
            for db_page in db_pages:
                if 'url' in db_page:
                    url = db_page['url']
                    page = Page(url, db_page)
                    pages.append(page)
                return pages
        except Exception, e:
            print str(e)
        finally:
            client.close()

    @staticmethod
    def exists(url):
        try:
            client = MongoClient()
            db = client.wiki
            db_page = db.wiki.find_one({'url': url})
            if db_page is not None and url in db_page['url']:
                return True
            return False
        except Exception, e:
            print str(e)
        finally:
            client.close()

    def delete(self, url):
        try:
            client = MongoClient()
            db = client.wiki
            result = db.wiki.delete_one({'url': url})
            if result is not None and 1 in result['deleted_count']:
                return True
            return False
        except Exception, e:
            print str(e)
        finally:
            client.close()

    def insert(self, url, title, tags, body):
            try:
                client = MongoClient()
                db = client.wiki
                if self.exists(url):
                    # Update page
                    page_id = self.get_page(url)
                    page_id = page_id['_id']
                    db.wiki.update_one({'_id': page_id}, {'$set': {'url': url, 'title': title, 'tags': tags, 'body': body}}, {'upsert': 'true'})
                    return True
                else:
                    # Create new page
                    db.wiki.insert_one({'url': url, 'title': title, 'tags': tags, 'body': body})
                    return True
            except Exception, e:
                print str(e)
            finally:
                client.close()
            return False


class Wiki(object):
    def __init__(self, root):
        self.root = root

    def path(self, url):
        return os.path.join(self.root, url + '.md')

    def exists(self, url):
        my_db = Db
        return my_db.exists(url)

    def get(self, url):
        my_db = Db()
        return my_db.get_page(url)

    def get_or_404(self, url):
        page = self.get(url)
        if page:
            return page
        abort(404)

    def get_bare(self, url):
        my_db = Db()
        if self.exists(url):
            return False
        return Page(url, '', new=True)

    def move(self, url, newurl):
        source = os.path.join(self.root, url) + '.md'
        target = os.path.join(self.root, newurl) + '.md'
        # normalize root path (just in case somebody defined it absolute,
        # having some '../' inside) to correctly compare it to the target
        root = os.path.normpath(self.root)
        # get root path longest common prefix with normalized target path
        common = os.path.commonprefix((root, os.path.normpath(target)))
        # common prefix length must be at least as root length is
        # otherwise there are probably some '..' links in target path leading
        # us outside defined root directory
        if len(common) < len(root):
            raise RuntimeError(
                'Possible write attempt outside content directory: '
                '%s' % newurl)
        # create folder if it does not exists yet
        folder = os.path.dirname(target)
        if not os.path.exists(folder):
            os.makedirs(folder)
        os.rename(source, target)

    def delete(self, url):
        my_db = Db()
        my_db.delete(url)

    def index(self):
        """
            Builds up a list of all the available pages.

            :returns: a list of all the wiki pages
            :rtype: list
        """
        my_db = Db()
        pages = my_db.get_pages()
        if pages is not None:
            return sorted(pages, key=lambda x: x.title.lower())
        return None

    def index_by(self, key):
        """
            Get an index based on the given key.

            Will use the metadata value of the given key to group
            the existing pages.

            :param str key: the attribute to group the index on.

            :returns: Will return a dictionary where each entry holds
                a list of pages that share the given attribute.
            :rtype: dict
        """
        pages = {}
        for page in self.index():
            value = getattr(page, key)
            pre = pages.get(value, [])
            pages[value] = pre.append(page)
        return pages

    def get_by_title(self, title):
        pages = self.index(attr='title')
        return pages.get(title)

    def get_tags(self):
        pages = self.index()
        tags = {}
        if pages is not None:
            for page in pages:
                pagetags = page.tags.split(',')
                for tag in pagetags:
                    tag = tag.strip()
                    if tag == '':
                        continue
                    elif tags.get(tag):
                        tags[tag].append(page)
                    else:
                        tags[tag] = [page]
            return tags
        return None

    def index_by_tag(self, tag):
        pages = self.index()
        tagged = []
        for page in pages:
            if tag in page.tags:
                tagged.append(page)
        return sorted(tagged, key=lambda x: x.title.lower())

    def search(self, term, ignore_case=True, attrs=['title', 'tags', 'body']):
        pages = self.index()
        regex = re.compile(term, re.IGNORECASE if ignore_case else 0)
        matched = []
        if pages is not None:
            for page in pages:
                for attr in attrs:
                    if regex.search(getattr(page, attr)):
                        matched.append(page)
                        break
            return matched
        return None

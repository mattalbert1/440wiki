from io import open
import os
import shutil
from tempfile import mkdtemp
from tempfile import mkstemp
from unittest import TestCase
from werkzeug.local import LocalProxy
from flask import current_app
from flask import g
from wiki.core import Wiki
from wiki.web import create_app


#: the default configuration
CONFIGURATION = u"""
PRIVATE=False
TITLE='test'
DEFAULT_SEARCH_IGNORE_CASE=False
DEFAULT_AUTHENTICATION_METHOD='cleartext'
TESTING=True
WTF_CSRF_ENABLED=False
SECRET_KEY='a unique and long key'
HISTORY_SHOW_MAX=30
PIC_BASE = '/static/content/'
CONTENT_DIR = '/Users/Matt/PycharmProjects/Riki/content'
USER_DIR = '/Users/Matt/PycharmProjects/Riki/user'
"""
# I had to add SECRET_KEY and WTF_CSRF_SECRET_KEY to configuration file so that the unit tests for
# test_user_add_delete.py could actually access other routes of the system.


class WikiBaseTestCase(TestCase):

    #: The contents of the ``config.py`` file.
    config_content = CONFIGURATION

    def setUp(self):
        """
            Creates a content directory for the wiki to use
            and adds a configuration file with some example content.
        """
        self._wiki = None
        self._app = None
        self.rootdir = mkdtemp()
        self.create_file(u'config.py', self.config_content)

    @property
    def wiki(self):
        if not self._wiki:
            self._wiki = Wiki(self.rootdir)
        return self._wiki

    """login_helper used to facilitate unit-test login attempts"""

    def login_helper(self, username, password):
        return self.app.post(
            '/user/login/',
            data=dict(name=username, password=password, form=""),
            follow_redirects=True
        )

    """user_create_helper used to facilitate unit-test user creation attempts"""

    def user_create_helper(self, username, password):
        return self.app.post(
            '/user/create/',
            data=dict(name=username, password=password, form=""),
            follow_redirects=True
        )

    """user_delete_helper used to facilitate unit-test user deletion attempts"""

    def user_delete_helper(self, username, password):
        return self.app.post(
            '/user/delete/'+username,
            data=dict(password=password, form=""),
            follow_redirects=True
        )

    @property
    def app(self):
        if not self._app:
            self._app = create_app(self.rootdir).test_client()
        return self._app

    def create_file(self, name, content=u'', folder=None):
        """
            Easy way to create a file.

            :param unicode name: the name of the file to create
            :param unicode content: content of the file (optional)
            :param unicode folder: the folder where the file should be
                created, defaults to the temporary directory

            :returns: the absolute path of the newly created file
            :rtype: unicode
        """
        if folder is None:
            folder = self.rootdir

        path = os.path.join(folder, name)

        if not os.path.exists(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))

        with open(path, 'w', encoding='utf-8') as fhd:
            fhd.write(content)

        return path

    def tearDown(self):
        """
            Will remove the root directory and all contents if one
            exists.
        """
        if self.rootdir and os.path.exists(self.rootdir):
            shutil.rmtree(self.rootdir)

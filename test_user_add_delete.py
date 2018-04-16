"""Test cases for accessing new APIs for creating and deleting user accounts in the wiki system"""
import unittest
from tests import WikiBaseTestCase


class TestAccountFeatures(WikiBaseTestCase):

        # Tests to confirm the access of new API pages

        """test_get_login attempts to load login interface page."""

        def test_get_login(self):
                response = self.app.get('/user/login/', follow_redirects=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('Login', response.data)

        """test_login attempts to login to wiki system. Necessary step because if we can't login, there is likely something
        wrong with the system, and we won't be able to test the delete user API"""

        def test_login(self):
            self.app.get('/user/login/', follow_redirects=True)
            response = self.login_helper("name", "1234")
            #print(response.data) # Can be used to view redirected page contents of the response
            self.assertEqual(response.status_code, 200)

        """test_create_user creates a new user for the user.json database file. It seems like a simple test, but was
        surprisingly troublesome during implementation stages, due to multiple configuration factors and app context
        issues. It works quite well though!"""

        """Note, without a "Delete User" test active, you will have to change the new user name each time, otherwise
        this test won't do anything (even though it may look like it succeeded) because the user_create API will reject
        the pre-existing username."""

        def test_create_user(self):
            self.app.get('/user/create/', follow_redirects=True)
            response = self.user_create_helper("testing", "123")
            #print(response.data) # Can be used to view redirected page contents of the response
            self.assertEqual(response.status_code, 200)
            self.app.get('/user/login/', follow_redirects=True)
            response = self.login_helper("testing", "123")
            user = self.app.current_users.get_user("testing")
            assert user is not None
            self.assertEqual(response.status_code, 200)
            self.assertIn("World", response)

        """test_delete_user attempts to delete the user created from the previous test_create_user unittest"""

        def test_delete_user(self):
            self.app.get('/user/login/', follow_redirects=True)
            response1 = self.login_helper("name", "1234")
            self.assertIn("World", response1)
            self.app.get('/user/delete/testing', follow_redirects=True)
            response1 = self.user_delete_helper("testing", "123")
            user = self.app.curent_users.get_user("testing")
            assert user is False
            self.assertEqual(response1.status_code, 200)


if __name__ == '__main__':
        unittest.main()

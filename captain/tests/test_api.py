import captain_web
import json
import os
import logging
import unittest
from captain import exceptions
from mock import patch
from nose.tools import eq_

os.environ["SLUG_RUNNER_COMMAND"] = ''
os.environ["SLUG_RUNNER_IMAGE"] = ''


class TestApi(unittest.TestCase):

    def setUp(self):
        self.test_app = captain_web.app.test_client()
        log = logging.getLogger('werkzeug')
        log.disabled = True

    def test_get_ping(self):
        """
        Call the ping endpoint
        It should return a 200
        """
        test_response = self.test_app.get('/ping/ping')
        eq_(test_response.status_code, 204)

    @patch('captain_web.Connection.start_instance')
    def test_start_instance_with_capacity_error(self, mock_captain_connection_start_instance):
        """
        When starting an instance and there are not enough slots we should have a 503 response with a json body containing the detail
        """
        mock_captain_connection_start_instance.side_effect = exceptions.NodeOutOfCapacityException()
        headers = [('Content-Type', 'application/json')]
        payload = dict(node='node-1')
        test_response = self.test_app.post('/instances/', headers=headers, data=json.dumps(payload))
        mock_captain_connection_start_instance.called_with('graham')
        eq_(test_response.content_type, 'application/json')
        eq_(json.loads(test_response.data), {"description": "There aren't enough free slots on node-1 to service your request"})
        eq_(test_response.status_code, 503)

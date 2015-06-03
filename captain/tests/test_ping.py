import captain_web
import os
from nose.tools import eq_

os.environ["SLUG_RUNNER_COMMAND"] = ''
os.environ["SLUG_RUNNER_IMAGE"] = ''

test_app = captain_web.app.test_client()


def test_get_ping():
    """
    Call the ping endpoint
    It should return a 200
    """
    test_response = test_app.get('/ping/ping')
    eq_(test_response.status_code, 204)

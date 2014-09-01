import unittest
import docker
from mock import patch, MagicMock
from captain.connection import Connection
from captain.tests import util_mock
# from util_mock import ClientMock
from captain.tests.util_mock import ClientMock


class TestConnection(unittest.TestCase):

    @patch('docker.Client')
    def test_returns_all_applications(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://user:pass@node-1:80/"], api_version="1.12")
        all_applications = connection.get_applications()

        # then
        self.assertEqual(2, all_applications.__len__())

        app_ers = all_applications["ers-checking-frontend-27"]
        self.assertEqual(1, app_ers.__len__())
        self.assertEqual("656ca7c307d178", app_ers[0]["id"])
        self.assertEqual("node-1", app_ers[0]["node"])
        self.assertEqual("ers-checking-frontend-27", app_ers[0]["app"])
        self.assertEqual(None, app_ers[0]["version"])
        self.assertEqual("node-1", app_ers[0]["address"])
        self.assertEqual(9225, app_ers[0]["port"])

        app_paye = all_applications["paye"]
        self.assertEqual(1, app_paye.__len__())
        self.assertEqual("eba8bea2600029", app_paye[0]["id"])
        self.assertEqual("node-1", app_paye[0]["node"])
        self.assertEqual("paye", app_paye[0]["app"])
        self.assertEqual("216", app_paye[0]["version"])
        self.assertEqual("node-1", app_paye[0]["address"])
        self.assertEqual(9317, app_paye[0]["port"])

import unittest
from mock import patch
from captain.connection import Connection
from captain.tests.util_mock import ClientMock


class TestConnection(unittest.TestCase):

    @patch('docker.Client')
    def test_returns_all_applications(self, docker_client):
        # given
        ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
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
        self.assertEqual(2, app_paye.__len__())
        self.assertEqual("eba8bea2600029", app_paye[0]["id"])
        self.assertEqual("node-1", app_paye[0]["node"])
        self.assertEqual("paye", app_paye[0]["app"])
        self.assertEqual("216", app_paye[0]["version"])
        self.assertEqual("node-1", app_paye[0]["address"])
        self.assertEqual(9317, app_paye[0]["port"])
        self.assertEqual("80be2a9e62ba00", app_paye[1]["id"])
        self.assertEqual("node-2", app_paye[1]["node"])
        self.assertEqual("paye", app_paye[1]["app"])
        self.assertEqual("216", app_paye[1]["version"])
        self.assertEqual("node-2", app_paye[1]["address"])
        self.assertEqual(9317, app_paye[1]["port"])

    @patch('docker.Client')
    def test_stops_application_running_on_single_node(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        connection.stop_application("ers-checking-frontend-27")

        # then
        mock_client_node1.stop.assert_called_with('656ca7c307d178')
        mock_client_node1.remove_container.assert_called_with('656ca7c307d178', force=True)

        self.assertFalse(mock_client_node2.stop.called)
        self.assertFalse(mock_client_node2.remove_container.called)

    @patch('docker.Client')
    def test_stops_application_running_on_two_nodes(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        connection.stop_application("paye")

        # then
        mock_client_node1.stop.assert_called_with('eba8bea2600029')
        mock_client_node1.remove_container.assert_called_with('eba8bea2600029', force=True)

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

    @patch('docker.Client')
    def test_stops_application_even_if_remove_container_fails(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)
        mock_client_node1.remove_container.side_effect = Exception()
        mock_client_node2.remove_container.side_effect = Exception()

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        connection.stop_application("paye")

        # then
        mock_client_node1.stop.assert_called_with('eba8bea2600029')
        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
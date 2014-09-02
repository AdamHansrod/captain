import unittest
from mock import patch
from captain.connection import Connection
from captain.tests.util_mock import ClientMock


class TestConnection(unittest.TestCase):

    @patch('docker.Client')
    def test_returns_all_instances(self, docker_client):
        # given
        ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        instances = connection.get_instances()

        # then
        self.assertEqual(3, instances.__len__())

        instance1 = instances[0]
        self.assertEqual("656ca7c307d178", instance1["id"])
        self.assertEqual("node-1", instance1["node"])
        self.assertEqual("ers-checking-frontend-27", instance1["app"])
        self.assertEqual(None, instance1["version"])
        self.assertEqual("node-1", instance1["address"])
        self.assertEqual(9225, instance1["port"])

        instance2 = instances[1]
        self.assertEqual("eba8bea2600029", instance2["id"])
        self.assertEqual("node-1", instance2["node"])
        self.assertEqual("paye", instance2["app"])
        self.assertEqual("216", instance2["version"])
        self.assertEqual("node-1", instance2["address"])
        self.assertEqual(9317, instance2["port"])

        instance3 = instances[2]
        self.assertEqual("80be2a9e62ba00", instance3["id"])
        self.assertEqual("node-2", instance3["node"])
        self.assertEqual("paye", instance3["app"])
        self.assertEqual("216", instance3["version"])
        self.assertEqual("node-2", instance3["address"])
        self.assertEqual(9317, instance3["port"])

    @patch('docker.Client')
    def test_stops_instance(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertFalse(mock_client_node1.stop.called)
        self.assertFalse(mock_client_node1.remove_container.called)

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

    @patch('docker.Client')
    def test_stops_instance_even_if_remove_container_fails(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)
        mock_client_node2.remove_container.side_effect = Exception()

        # when
        connection = Connection(nodes=["http://node-1/", "http://node-2/"], api_version="1.12")
        connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertFalse(mock_client_node1.stop.called)
        self.assertFalse(mock_client_node1.remove_container.called)

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

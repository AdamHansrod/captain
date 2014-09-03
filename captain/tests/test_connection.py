import unittest
from mock import patch
from captain.config import Config
from captain.connection import Connection
from captain.tests.util_mock import ClientMock


class TestConnection(unittest.TestCase):

    def setUp(self):
        self.config = Config()
        self.config.docker_nodes = ["http://node-1/", "http://node-2/"]

    @patch('docker.Client')
    def test_returns_all_instances(self, docker_client):
        # given
        ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config)
        instances = connection.get_instances()

        # then
        self.assertEqual(3, instances.__len__())

        instance1 = instances[0]
        self.assertEqual("656ca7c307d178", instance1["id"])
        self.assertEqual("ers-checking-frontend-27", instance1["app"])
        self.assertEqual(None, instance1["version"])
        self.assertEqual("node-1", instance1["node"])
        self.assertEqual(9225, instance1["port"])
        self.assertEqual(2, instance1["environment"].__len__())
        self.assertEqual("-Dapplication.secret=H7dVw$PlJiD)^U,oa4TA1pa]pT:4ETLqbL&2P=n6T~p,A*}^.Y46@PQOV~9(B09Hc]t7-hsf~&@w=zH -Dapplication.log=INFO -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080 -Dgovuk-tax.Prod.google-analytics.token=UA-43414424-2 -Drun.mode=Prod -Dsession.secure=true -Dsession.httpOnly=true -Dcookie.encryption.key=fqpLDZ4smuDsekHkrEBlCA==", instance1["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance1["environment"]["JAVA_OPTS"])

        instance2 = instances[1]
        self.assertEqual("eba8bea2600029", instance2["id"])
        self.assertEqual("paye", instance2["app"])
        self.assertEqual("216", instance2["version"])
        self.assertEqual("node-1", instance2["node"])
        self.assertEqual(9317, instance2["port"])
        self.assertEqual(2, instance2["environment"].__len__())
        self.assertEqual("-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080", instance2["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance2["environment"]["JAVA_OPTS"])

        instance3 = instances[2]
        self.assertEqual("80be2a9e62ba00", instance3["id"])
        self.assertEqual("paye", instance3["app"])
        self.assertEqual("216", instance3["version"])
        self.assertEqual("node-2", instance3["node"])
        self.assertEqual(9317, instance3["port"])
        self.assertEqual(2, instance3["environment"].__len__())
        self.assertEqual("-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080", instance3["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance3["environment"]["JAVA_OPTS"])

    @patch('docker.Client')
    def test_stops_instance(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config)
        result = connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertTrue(result)

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
        connection = Connection(self.config)
        result = connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertTrue(result)

        self.assertFalse(mock_client_node1.stop.called)
        self.assertFalse(mock_client_node1.remove_container.called)

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

    @patch('docker.Client')
    def test_returns_false_when_trying_to_stop_nonexisting_instance(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2) = ClientMock().mock_two_docker_nodes(docker_client)
        mock_client_node2.remove_container.side_effect = Exception()

        # when
        connection = Connection(self.config)
        result = connection.stop_instance("nonexisting-instance")

        # then
        self.assertFalse(result)

        self.assertFalse(mock_client_node1.stop.called)
        self.assertFalse(mock_client_node1.remove_container.called)

        self.assertFalse(mock_client_node2.stop.called)
        self.assertFalse(mock_client_node2.remove_container.called)

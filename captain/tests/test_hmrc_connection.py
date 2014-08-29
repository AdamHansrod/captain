import unittest
from mock import patch
from captain.hmrc_connection import Connection
from captain.hmrc_model import Instance
from util_mock import ClientMock, containers


class TestConnection(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = Connection(nodes=["http://user:pass@localhost:80/"])

    def test_returns_connection(self):
        self.assertEquals(type(self.connection), Connection)
        self.assertTrue(self.MockDockerClient.called)

    def test_get_container(self):
        node = "localhost"
        container_details = containers[0]
        container_id = container_details["id"]
        container1 = self.connection.get_container(node, container_id)
        container2 = Instance(self.MockDockerClient(), node, container_id)
        different_container_id = containers[1]["id"]
        different_container = Instance(self.MockDockerClient(), node, different_container_id)
        self.assertEquals(container1, container2)
        self.assertNotEquals(container1, different_container)


class TestWeirdContainersPresent(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = Connection(nodes=["http://user:pass@localhost:80/"])

    def test_one_or_more_containers_with_no_version(self):
        containers_with_no_version_set = [c for a in self.connection.get_all_apps().values() for c in a if not c["version"]]
        self.assertTrue(len(containers_with_no_version_set) > 0)

    def test_one_or_more_containers_not_running(self):
        not_running_containers = [c for a in self.connection.get_all_apps().values() for c in a if not c["running"]]
        self.assertTrue(len(not_running_containers) > 0)

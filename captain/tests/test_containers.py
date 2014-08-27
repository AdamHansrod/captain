import unittest
import captain
from mock import patch
from mocked_dockerpy_output import ClientMock, containers


class TestConnection(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = captain.Connection(nodes=["http://user:pass@localhost:80/"])

    def test_returns_connection(self):
        self.assertEquals(type(self.connection), captain.Connection)
        self.assertTrue(self.MockDockerClient.called)

    def test_get_container(self):
        node = "localhost"
        container_details = containers[0]
        container_id = container_details["id"]
        container1 = self.connection.get_container(node, container_id)
        container2 = captain.Container(self.MockDockerClient(), node, container_id)
        different_container_id = containers[1]["id"]
        different_container = captain.Container(self.MockDockerClient(), node, different_container_id)
        self.assertEquals(container1, container2)
        self.assertNotEquals(container1, different_container)


class TestApp(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = captain.Connection(nodes=["http://user:pass@localhost:80/"])

    def test_apps(self):
        node = "localhost"
        app_name = containers[0]["app"]
        app_containers = []
        for container_details in containers:
            if container_details["app"] != app_name:
                continue
            app_container_id = container_details["id"]
            app_containers.append(captain.Container(self.MockDockerClient(), node, app_container_id))
        app = captain.App(name=app_name, containers=app_containers)
        self.assertEquals(app, self.connection.get_all_apps()[app_name])
        self.assertTrue(len(app) > 0)


class TestWierdContainersPresent(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = captain.Connection(nodes=["http://user:pass@localhost:80/"])

    def test_one_or_more_containers_with_no_version(self):
        containers_with_no_version_set = [c for a in self.connection.get_all_apps().values() for c in a if not c["version"]]
        self.assertTrue(len(containers_with_no_version_set) > 0)

    def test_one_or_more_containers_not_running(self):
        not_running_containers = [c for a in self.connection.get_all_apps().values() for c in a if not c["running"]]
        self.assertTrue(len(not_running_containers) > 0)


class TestContainer(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def get_container(self, container_details):
        return captain.Container(
            docker_connection=self.MockDockerClient(),
            node="localhost",
            container_id=container_details["id"])

    def test_container_name_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["app"], container_details["app"])

    def test_container_version_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["version"], container_details["version"])

    def test_container_node_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["node"], "localhost")

    def test_container_ip_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(self.container["ip"], "127.0.0.1")

    def test_container_port_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["port"], container_details["port"])

    def test_container_running_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["running"], container_details["running"])

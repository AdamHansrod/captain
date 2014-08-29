import unittest
import socket
from mock import patch
from captain.hmrc_connection import Connection
from captain.hmrc_model import Instance, Application
from util_mock import ClientMock, containers


class TestApplication(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = Connection(nodes=["http://user:pass@localhost:80/"])

    def test_apps(self):
        node = "localhost"
        app_name = containers[0]["app"]
        app_containers = []
        for container_details in containers:
            if container_details["app"] != app_name:
                continue
            app_container_id = container_details["id"]
            app_containers.append(Instance(self.MockDockerClient(), node, app_container_id))
        app = Application(name=app_name, instances=app_containers)
        self.assertEquals(app, self.connection.get_all_apps()[app_name])
        self.assertTrue(len(app) > 0)


class TestContainer(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def get_container(self, container_details):
        return Instance(
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
            self.assertEqual(container["ip"], socket.gethostbyname("localhost"))

    def test_container_port_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["port"], container_details["port"])

    def test_container_running_attribute(self):
        for container_details in containers:
            container = self.get_container(container_details)
            self.assertEqual(container["running"], container_details["running"])

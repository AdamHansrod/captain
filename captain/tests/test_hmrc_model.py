import unittest
import socket
from mock import patch
from captain.hmrc_connection import Connection
from captain.hmrc_model import Instance, Application
from util_mock import ClientMock, containers, __inspect_container_cmd_return, container_details


class TestApplication(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = Connection(nodes=["http://user:pass@localhost:80/"])

    def test_apps(self):
        node = "localhost"
        app_name = containers[0]["app"]
        app_containers = []
        for container in containers:
            if container["app"] != app_name:
                continue
            app_container_id = container["id"]
            app_containers.append(Instance(app_container_id, container_details[container["id"]], node))
        app = Application(name=app_name, instances=app_containers)
        self.assertEquals(app, self.connection.get_all_apps()[app_name])
        self.assertTrue(len(app) > 0)


class TestContainer(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def build_instance(self, container):
        return Instance(
            inspection_details=container_details[container["id"]],
            node="localhost",
            container_id=container["id"])

    def test_container_name_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual(container["app"], instance["app"])

    def test_container_version_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual(container["version"], instance["version"])

    def test_container_node_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual("localhost", instance["node"])

    def test_container_ip_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual(socket.gethostbyname("localhost"), instance["ip"])

    def test_container_port_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual(container["port"], instance["port"])

    def test_container_running_attribute(self):
        for container in containers:
            instance = self.build_instance(container)
            self.assertEqual(container["running"], instance["running"])

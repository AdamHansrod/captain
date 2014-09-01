import unittest
from captain.model import ApplicationInstance, Application


class TestApplication(unittest.TestCase):

    def test_creation(self):
        # given
        app_name = "paye"
        app_instance_1 = ApplicationInstance("abcdef0123456789", "paye", "1.2.0", "node-1", "192.168.17.6", 43127)
        app_instance_2 = ApplicationInstance("abcdef9876543210", "paye", "1.2.0", "node-2", "192.168.17.7", 43053)

        # when
        application = Application(name=app_name, instances=[app_instance_1, app_instance_2])

        # then
        self.assertEquals(app_name, application.name)
        self.assertEquals(app_instance_1, application[0])
        self.assertEquals(app_instance_2, application[1])


class TestApplicationInstance(unittest.TestCase):

    def test_creation(self):
        # given
        id = "abcdef0123456789"
        app = "paye"
        version = "1.2.0"
        node = "appserver-1"
        address = "192.168.17.6"
        port = 43127

        # when
        instance = ApplicationInstance(id, app, version, node, address, port)

        # then
        self.assertEqual(id, instance["id"])
        self.assertEqual(app, instance["app"])
        self.assertEqual(version, instance["version"])
        self.assertEqual(node, instance["node"])
        self.assertEqual(address, instance["address"])
        self.assertEqual(port, instance["port"])
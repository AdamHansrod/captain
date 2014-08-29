import unittest
from captain.hmrc_model import Instance, Application


class TestApplication(unittest.TestCase):

    def test_creation(self):
        # given
        app_name = "paye"
        app_instance_1 = Instance("abcdef0123456789", "paye", "1.2.0", "appserver-1", "192.168.17.6", 43127, True)
        app_instance_2 = Instance("abcdef9876543210", "paye", "1.2.0", "appserver-2", "192.168.17.7", 43053, True)

        # when
        application = Application(name=app_name, instances=[app_instance_1, app_instance_2])

        # then
        self.assertEquals(app_name, application.name)
        self.assertEquals(app_instance_1, application[0])
        self.assertEquals(app_instance_2, application[1])


class TestInstance(unittest.TestCase):

    def test_creation(self):
        # given
        id = "abcdef0123456789"
        app = "paye"
        version = "1.2.0"
        node = "appserver-1"
        ip = "192.168.17.6"
        port = 43127
        running = True

        # when
        instance = Instance(id, app, version, node, ip, port, running)

        # then
        self.assertEqual(id, instance["id"])
        self.assertEqual(app, instance["app"])
        self.assertEqual(version, instance["version"])
        self.assertEqual(node, instance["node"])
        self.assertEqual(ip, instance["ip"])
        self.assertEqual(port, instance["port"])
        self.assertEqual(running, instance["running"])

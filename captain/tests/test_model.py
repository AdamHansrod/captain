import unittest
from captain.model import Instance


class TestInstance(unittest.TestCase):

    def test_creation(self):
        # given
        id = "abcdef0123456789"
        app = "paye"
        version = "1.2.0"
        node = "appserver-1"
        address = "192.168.17.6"
        port = 43127

        # when
        instance = Instance(id, app, version, node, address, port)

        # then
        self.assertEqual(id, instance["id"])
        self.assertEqual(app, instance["app"])
        self.assertEqual(version, instance["version"])
        self.assertEqual(node, instance["node"])
        self.assertEqual(address, instance["address"])
        self.assertEqual(port, instance["port"])
import unittest
from captain.model import Instance


class TestInstance(unittest.TestCase):

    def test_creation(self):
        # given
        id = "abcdef0123456789"
        app = "paye"
        version = "1.2.0"
        node = "appserver-1"
        port = 43127

        # when
        instance = Instance(id, app, version, node, port)

        # then
        self.assertEqual(id, instance["id"])
        self.assertEqual(app, instance["app"])
        self.assertEqual(version, instance["version"])
        self.assertEqual(node, instance["node"])
        self.assertEqual(port, instance["port"])
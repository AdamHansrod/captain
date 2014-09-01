import unittest
from mock import patch
from captain.connection import Connection
from util_mock import ClientMock


class TestConnection(unittest.TestCase):
    MockDockerClient = ClientMock()

    @patch('docker.Client', new=MockDockerClient)
    def setUp(self):
        self.connection = Connection(nodes=["http://user:pass@localhost:80/"])

    def test_creates_docker_client(self):
        self.assertTrue(self.MockDockerClient.called)

    def test_returns_all_apps(self):
        # when
        all_apps = self.connection.get_all_apps()

        # then
        self.assertEqual(3, all_apps.__len__())

        app_ers = all_apps["ers-checking-frontend-27"]
        self.assertEqual(1, app_ers.__len__())
        self.assertEqual("656ca7c307d178", app_ers[0]["id"])
        self.assertEqual("ers-checking-frontend-27", app_ers[0]["app"])
        self.assertEqual(None, app_ers[0]["version"])
        self.assertEqual(9225, app_ers[0]["port"])
        self.assertEqual(True, app_ers[0]["running"])

        app_paye = all_apps["paye"]
        self.assertEqual(1, app_paye.__len__())
        self.assertEqual("eba8bea2600029", app_paye[0]["id"])
        self.assertEqual("paye", app_paye[0]["app"])
        self.assertEqual("216", app_paye[0]["version"])
        self.assertEqual(9317, app_paye[0]["port"])
        self.assertEqual(True, app_paye[0]["running"])

        app_attorney = all_apps["attorney"]
        self.assertEqual(1, app_attorney.__len__())
        self.assertEqual("1ca0e49fcd60fa", app_attorney[0]["id"])
        self.assertEqual("attorney", app_attorney[0]["app"])
        self.assertEqual("46", app_attorney[0]["version"])
        self.assertEqual(9344, app_attorney[0]["port"])
        self.assertEqual(False, app_attorney[0]["running"])

    def test_one_or_more_containers_with_no_version(self):
        containers_with_no_version_set = [c for a in self.connection.get_all_apps().values() for c in a if not c["version"]]
        self.assertTrue(len(containers_with_no_version_set) > 0)

    def test_one_or_more_containers_not_running(self):
        not_running_containers = [c for a in self.connection.get_all_apps().values() for c in a if not c["running"]]
        self.assertTrue(len(not_running_containers) > 0)

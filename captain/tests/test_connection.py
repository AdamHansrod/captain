import logging
import unittest
from mock import patch, MagicMock, call
from captain.connection import Connection
from captain import exceptions
from captain.tests.util_mock import ClientMock
from requests.exceptions import ConnectionError
from testfixtures import LogCapture
import itertools


class TestConnection(unittest.TestCase):

    def setUp(self):
        self.config = MagicMock()
        self.config.docker_nodes = ["http://node-1/", "http://node-2/", "http://node-3/"]
        self.config.slug_runner_command = "runner command"
        self.config.slug_runner_image = "runner/image"
        self.config.slug_runner_version = "0.0.73"
        self.config.docker_gc_grace_period = 86400
        self.config.slots_per_node = 10
        self.config.slot_memory_mb = 128
        self.config.default_slots_per_instance = 2
        self.config.aws_docker_host_tag_name = None
        self.config.aws_docker_host_tag_value = None

        self.aws_host_resolver = MagicMock()

    @patch('docker.Client')
    def test_returns_summary_of_instances(self, docker_client):
        # given
        (docker_conn1, docker_conn2, docker_conn3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config)
        summary = connection.get_instance_summary()

        # then
        print summary
        self.assertEqual(3, summary['total_instances'])
        self.assertEqual(1, summary['apps']['ers-checking-frontend-27'])
        self.assertEqual(2, summary['apps']['paye'])

    @patch('docker.Client')
    def test_logs_exception_when_docker_nodes_config_is_bad(self, docker_client):
        """
        With three nodes configured but with one bad node an error should be logged but 2 nodes should be returned
        """
        # given
        (docker_conn1, docker_conn2, docker_conn3) = ClientMock().mock_two_docker_nodes(docker_client)
        expected_nodes = ['node-1', 'node-2']

        # when
        self.config.docker_nodes = ["http://node-1/", "http://node-2/", "http://node-3]"]

        # given
        with LogCapture(names='connection', level=logging.ERROR) as l:
            connection = Connection(self.config)
            l.check(
                ('connection', 'ERROR', 'Failed to add node from config: http://node-3]')
            )
            nodes = connection.get_nodes()
            self.assertTrue(len(nodes) == 2)
            for node in nodes:
                self.assertIn(node['id'], expected_nodes)

    @patch('docker.Client')
    def test_returns_all_instances_with_ports(self, docker_client):
        # given
        (docker_conn1, docker_conn2, docker_conn3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        #   get_instances is async and order isn't guaranteed, sort it for the tests
        instances = sorted(connection.get_instances(), key=lambda i: i["id"])

        # then
        self.assertEqual(3, instances.__len__())

        instance1 = instances[0]
        self.assertEqual("656ca7c307d178", instance1["id"])
        self.assertEqual("ers-checking-frontend-27", instance1["app"])
        self.assertEqual("node-1", instance1["node"])
        self.assertEqual(9225, instance1["port"])
        self.assertEqual("https://host/ers-checking-frontend_27.tgz", instance1["slug_uri"])
        self.assertEqual(2, instance1["environment"].__len__())
        self.assertEqual("-Dapplication.secret=H7dVw$PlJiD)^U,oa4TA1pa]pT:4ETLqbL&2P=n6T~p,A*}^.Y46@PQOV~9(B09Hc]t7-hsf~&@w=zH -Dapplication.log=INFO -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080 -Dgovuk-tax.Prod.google-analytics.token=UA-00000000-0 -Drun.mode=Prod -Dsession.secure=true -Dsession.httpOnly=true -Dcookie.encryption.key=fqpLDZ4smuDsekHkrEBlCA==", instance1["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance1["environment"]["JAVA_OPTS"])

        instance2 = instances[2]
        self.assertEqual("eba8bea2600029", instance2["id"])
        self.assertEqual("paye", instance2["app"])
        self.assertEqual("node-1", instance2["node"])
        self.assertEqual(9317, instance2["port"])
        self.assertEqual("https://host/paye_216.tgz", instance2["slug_uri"])
        self.assertEqual(2, instance2["environment"].__len__())
        self.assertEqual("-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080", instance2["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance2["environment"]["JAVA_OPTS"])

        instance3 = instances[1]
        self.assertEqual("80be2a9e62ba00", instance3["id"])
        self.assertEqual("paye", instance3["app"])
        self.assertEqual("node-2", instance3["node"])
        self.assertEqual(9317, instance3["port"])
        self.assertEqual(2, instance3["environment"].__len__())
        self.assertEqual("-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080", instance3["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", instance3["environment"]["JAVA_OPTS"])
        # One container stopped
        docker_conn1.remove_container.assert_has_calls([call("381587e2978216")])
        # One container with FinishedAt time of 0 removed
        docker_conn1.remove_container.assert_has_calls([call("3815178hgdasf6")])
        self.assertEqual(docker_conn1.remove_container.call_count, 2)
        self.assertEqual(docker_conn2.remove_container.call_count, 1)
        # jh23899fg00029 doesn't have captain ports defined and should be ignored.
        self.assertFalse([i for i in instances if i["id"] == "jh23899fg00029"])

        self.assertRaises(ConnectionError, docker_conn3.containers)

    @patch('docker.Client')
    @patch('uuid.uuid4')
    def test_starts_instance(self, uuid_mock, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)
        uuid_mock.return_value = 'SOME-UUID'

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        started_instance = connection.start_instance(
            "paye", "https://host/paye_216.tgz", "node-1", None,
            {'HMRC_CONFIG': "-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080",
             'JAVA_OPTS': "-Xmx256m -Xms256m"}, 2)

        # then
        self.assertEqual("eba8bea2600029", started_instance["id"])
        self.assertEqual("paye", started_instance["app"])
        self.assertEqual("node-1", started_instance["node"])
        self.assertEqual(9317, started_instance["port"])
        self.assertEqual("https://host/paye_216.tgz", started_instance["slug_uri"])
        self.assertEqual(2, started_instance["environment"].__len__())
        self.assertEqual("-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080", started_instance["environment"]["HMRC_CONFIG"])
        self.assertEqual("-Xmx256m -Xms256m", started_instance["environment"]["JAVA_OPTS"])
        self.assertEqual(2, started_instance["slots"])

        mock_client_node1.create_container.assert_called_with(image="{}:{}".format(self.config.slug_runner_image, str(self.config.slug_runner_version)),
                                                              command=self.config.slug_runner_command,
                                                              ports=[8080],
                                                              environment={
                                                                  'PORT': '8080',
                                                                  'SLUG_URL': 'https://host/paye_216.tgz',
                                                                  'HMRC_CONFIG': '-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080',
                                                                  'JAVA_OPTS': '-Xmx256m -Xms256m'
                                                              },
                                                              detach=True,
                                                              name="paye_SOME-UUID",
                                                              cpu_shares=2,
                                                              hostname=None,
                                                              mem_limit=256 * 1024 * 1024,
                                                              )

        connection.start_instance(
            "paye", "http://host/paye-216-slug.tgz", "node-1", None,
            {'HMRC_CONFIG': "-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080",
             'JAVA_OPTS': "-Xmx256m -Xms256m"})

        mock_client_node1.create_container.assert_called_with(image="{}:{}".format(self.config.slug_runner_image, str(self.config.slug_runner_version)),
                                                              command=self.config.slug_runner_command,
                                                              ports=[8080],
                                                              environment={
                                                                  'PORT': '8080',
                                                                  'SLUG_URL': 'http://host/paye-216-slug.tgz',
                                                                  'HMRC_CONFIG': '-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080',
                                                                  'JAVA_OPTS': '-Xmx256m -Xms256m'
                                                              },
                                                              detach=True,
                                                              name="paye_SOME-UUID",
                                                              cpu_shares=2,
                                                              mem_limit=256 * 1024 * 1024,
                                                              hostname=None,
                                                              )

        mock_client_node1.start.assert_called_with("eba8bea2600029", port_bindings={8080: None})

        self.assertFalse(mock_client_node2.create_container.called)
        self.assertFalse(mock_client_node2.start.called)

    @patch('docker.Client')
    @patch('uuid.uuid4')
    def test_starts_instance_on_specific_slug_runner_version(self, uuid_mock, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)
        uuid_mock.return_value = 'SOME-OTHER-UUID'

        # when
        connection = Connection(self.config)
        started_instance = connection.start_instance(
            "paye", "https://host/paye_216.tgz", "node-1", None,
            {'HMRC_CONFIG': "-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080",
             'JAVA_OPTS': "-Xmx256m -Xms256m"}, 2, None, "0.0.99")

        # then
        mock_client_node1.create_container.assert_called_with(image="{}:{}".format(self.config.slug_runner_image, "0.0.99"),
                                                              command=self.config.slug_runner_command,
                                                              ports=[8080],
                                                              environment={
                                                                  'PORT': '8080',
                                                                  'SLUG_URL': 'https://host/paye_216.tgz',
                                                                  'HMRC_CONFIG': '-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080',
                                                                  'JAVA_OPTS': '-Xmx256m -Xms256m'
                                                              },
                                                              detach=True,
                                                              name="paye_SOME-OTHER-UUID",
                                                              cpu_shares=2,
                                                              hostname=None,
                                                              mem_limit=256 * 1024 * 1024,
                                                              )

    @patch('docker.Client')
    def test_stops_instance(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        result = connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertTrue(result)

        self.assertFalse(mock_client_node1.stop.called)
        mock_client_node1.remove_container.assert_not_called_with("80be2a9e62ba00")

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

    @patch('docker.Client')
    def test_stops_instance_even_if_remove_container_fails(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        result = connection.stop_instance("80be2a9e62ba00")

        # then
        self.assertTrue(result)

        self.assertFalse(mock_client_node1.stop.called)
        mock_client_node1.remove_container.assert_not_called_with('80be2a9e62ba00')

        mock_client_node2.stop.assert_called_with('80be2a9e62ba00')
        mock_client_node2.remove_container.assert_called_with('80be2a9e62ba00', force=True)

    @patch('docker.Client')
    def test_returns_false_when_trying_to_stop_nonexisting_instance(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        result = connection.stop_instance("nonexisting-instance")

        # then
        self.assertFalse(result)

        self.assertFalse(mock_client_node1.stop.called)
        mock_client_node1.remove_container.assert_not_called_with('nonexisting-instance')

        self.assertFalse(mock_client_node2.stop.called)
        mock_client_node2.remove_container.assert_not_called_with('nonexisting-instance')

    @patch('docker.Client')
    def test_over_capacity(self, docker_client):
        # given
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config, self.aws_host_resolver)
        # Force an over capacity error
        current_slot_count = sum([i["slots"] for i in connection.get_instances() if i['node'] == 'node-1'])
        self.assertTrue(current_slot_count != self.config.slots_per_node)

        # then
        self.assertRaises(exceptions.NodeOutOfCapacityException,
                          connection.start_instance, "paye", "http://host/paye-216-slug.tgz", "node-1", None,
                          {'HMRC_CONFIG': "-Dapplication.log=INFO -Drun.mode=Prod -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080",
                           'JAVA_OPTS': "-Xmx256m -Xms256m"}, self.config.slots_per_node - current_slot_count + 1)

    @patch('docker.Client')
    def test_get_node_details(self, docker_client):
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)
        connection = Connection(self.config, self.aws_host_resolver)

        self.assertRaises(exceptions.NoSuchNodeException, connection.get_node, "bum-node-1")

        node_details = connection.get_node("node-1")
        self.assertDictEqual(
            {"id": "node-1",
             "slots": {"free": 6, "used": 4, "total": 10}, "state": "healthy"},
            node_details
        )

    @patch('docker.Client')
    def test_get_logs(self, docker_client):
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)
        connection = Connection(self.config, self.aws_host_resolver)

        self.assertRaises(exceptions.NoSuchInstanceException, connection.get_logs, "non-existant")

        instance_logs = connection.get_logs("80be2a9e62ba00")
        self.assertEqual(
            ({"msg": "this is line 1\n"}, {"msg": "this is line 2\n"}),
            tuple(itertools.islice(instance_logs, 2)))

        instance_logs = connection.get_logs("eba8bea2600029", follow=True)
        self.assertEqual(
            ({"msg": "this is line 1"}, {"msg": "this is line 2"}, {"msg": "this is line 3"}),
            tuple(itertools.islice(instance_logs, 3)))

    @patch('docker.Client')
    def test_get_nodes(self, docker_client):
        (mock_client_node1, mock_client_node2, mock_client_node3) = ClientMock().mock_two_docker_nodes(docker_client)
        connection = Connection(self.config, self.aws_host_resolver)

        nodes = connection.get_nodes()
        self.assertTrue(len(nodes) == 3)
        self.assertIn(
            {"id": "node-1",
             "slots": {"free": 6, "used": 4, "total": 10}, "state": "healthy"},
            nodes
        )

    @patch('docker.Client')
    def test_gc(self, docker_client):
        # given
        (docker_conn1, docker_conn2, docker_conn3) = ClientMock().mock_two_docker_nodes(docker_client)

        # when
        connection = Connection(self.config)
        # trigger gc
        connection.get_instances()

        # then
        # 61c2695fd82a is a freshly created but not yet started container and so shouldn't be gc'd
        self.assertNotIn(call("61c2695fd82a"), docker_conn2.start.mock_calls)

        # 61c2695fd82b is an old container with epoch start and exit times and should be gc'd
        docker_conn2.remove_container.assert_has_calls([call("61c2695fd82b")])

    def test_it_should_configure_docker_nodes_from_aws_when_config_contains_tag_value(self):
        # Given
        self.config = MagicMock()
        self.config.aws_docker_host_tag_name = "role"
        self.config.aws_docker_host_tag_value = "appserver"

        aws_host_ip_addresses = ['1.1.1.1', '2.2.2.2']
        self.aws_host_resolver.find_running_hosts_private_ip_by_tag = MagicMock(return_value=aws_host_ip_addresses)

        # When
        connection = Connection(self.config, self.aws_host_resolver)

        # Then
        self.aws_host_resolver\
            .find_running_hosts_private_ip_by_tag\
            .assert_called_once_with(self.config.aws_docker_host_tag_name,
                                     self.config.aws_docker_host_tag_value)

        self.assertEquals(2, len(connection.node_connections))
        for ip_address in aws_host_ip_addresses:
            self.assertIsNotNone(connection.node_connections[ip_address])
            self.assertEquals("https://{}:9400".format(ip_address), connection.node_connections[ip_address].base_url)
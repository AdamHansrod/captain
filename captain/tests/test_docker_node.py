import unittest

import mock
from mock import MagicMock

from captain.docker_node import ConfigBasedDockerNodeResolver, AWSDockerNodeResolver, DockerNodeResolverFactory


class TestConfigBasedDockerNodeResolver(unittest.TestCase):

    def test_it_should_return_the_docker_nodes(self):
        # Given
        docker_nodes = ['1.1.1.1', '2.2.2.2']

        # When
        under_test = ConfigBasedDockerNodeResolver(docker_nodes)

        # Then
        self.assertEquals(docker_nodes, under_test.get_docker_nodes())

    def test_it_should_raise_an_exception_when_docker_nodes_are_not_provided(self):
        # Given
        docker_nodes = []

        # When
        try:
            ConfigBasedDockerNodeResolver(docker_nodes)
            self.fail("Exception should have been thrown but was not.")
        # Then
        except Exception as e:
            self.assertEquals("docker_nodes provided was not provided but is mandatory.", e.message)


class TestAWSDockerNodeResolver(unittest.TestCase):

    def setUp(self):
        self.aws_docker_host_tag_name = 'role'
        self.aws_docker_host_tag_value = 'appservers'
        self.docker_proxy_username = "username"
        self.docker_proxy_password = "password"
        self.docker_nodes = ['1.1.1.1', '2.2.2.2']
        self.aws_host_resolver = MagicMock()
        self.under_test = AWSDockerNodeResolver(self.aws_host_resolver,
                                                self.aws_docker_host_tag_name,
                                                self.aws_docker_host_tag_value,
                                                self.docker_proxy_username,
                                                self.docker_proxy_password)

        self.aws_host_resolver.find_running_hosts_private_ip_by_tag = MagicMock(return_value=self.docker_nodes)

    def test_it_should_get_docker_hosts_from_aws(self):
        # When
        self.under_test.get_docker_nodes()

        # Then
        self.aws_host_resolver.find_running_hosts_private_ip_by_tag.assert_called_once_with(self.aws_docker_host_tag_name,
                                                                                            self.aws_docker_host_tag_value)

    def test_it_should_transform_aws_hosts_to_docker_nodes(self):
        # Given
        expected_docker_nodes = ['https://username:password@1.1.1.1:9400', 'https://username:password@2.2.2.2:9400']

        # When
        docker_nodes = self.under_test.get_docker_nodes()

        # Then
        self.assertListEqual(expected_docker_nodes, docker_nodes)


class TestDockerNodeResolverFactory(unittest.TestCase):

    def setUp(self):
        self.config = MagicMock()
        self.under_test = DockerNodeResolverFactory(self.config)

    def test_it_should_return_a_config_based_resolver(self):
        # Given
        self.config.aws_docker_host_tag_value = None
        self.config.docker_nodes = ['1.1.1.1']

        # When
        node_resolver = self.under_test.get_host_resolver()

        # Then
        self.assertIsInstance(node_resolver, ConfigBasedDockerNodeResolver)

    def test_it_should_return_an_aws_based_resolver(self):
        # Given
        self.config.aws_docker_host_tag_name = 'role'
        self.config.aws_docker_host_tag_value = 'appservers'
        self.config.aws_call_interval_secs = 180
        ec2_client = MagicMock
        aws_host_resolver = MagicMock

        # When
        with mock.patch.object(self.under_test, '_DockerNodeResolverFactory__create_ec2_client', return_value=ec2_client) as create_ec2_client_method:
            with mock.patch.object(self.under_test, '_DockerNodeResolverFactory__create_aws_host_resolver', return_value=aws_host_resolver) as create_aws_host_resolver_method:
                node_resolver = self.under_test.get_host_resolver()

                # Then
                self.assertIsInstance(node_resolver, AWSDockerNodeResolver)
                self.assertEquals(node_resolver.aws_host_resolver, aws_host_resolver)
                self.assertEquals(node_resolver.aws_docker_host_tag_name, self.config.aws_docker_host_tag_name)
                self.assertEquals(node_resolver.aws_docker_host_tag_value, self.config.aws_docker_host_tag_value)
                create_ec2_client_method.assert_called_once()
                create_aws_host_resolver_method.assert_called_once_with(ec2_client,
                                                                        self.config)
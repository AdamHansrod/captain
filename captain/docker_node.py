import abc
import logging
from abc import abstractmethod

import boto3

from captain.aws import AWSHostResolver


class DockerNodeResolverFactory(object):

    def __init__(self, config):
        self.logger = logging.getLogger(__name__)
        self.config = config

    def get_host_resolver(self):
        if self.config.aws_docker_host_tag_value is not None:
            self.logger.debug(dict(Message={"Creating AWS Docker Node Resolver"}))
            return self.__create_aws_docker_node_resolver(self.config)
        else:
            self.logger.debug(dict(Message={"Creating Config Based Docker Node Resolver"}))
            return self.__create_config_based_docker_node_resolver(self.config)

    def __create_ec2_client(self):
        ec2_client = boto3.client('ec2')
        self.logger.debug(dict(Message={"Created EC2 Client"}))
        return ec2_client

    def __create_aws_host_resolver(self, ec2_client, config):
        aws_host_resolver = AWSHostResolver(ec2_client,
                                            aws_call_interval_secs=config.aws_call_interval_secs)
        self.logger.debug(dict(Message={"Created AWSHostResolver"}))
        return aws_host_resolver

    def __create_aws_docker_node_resolver(self, config):
        ec2_client = self.__create_ec2_client()
        aws_host_resolver = self.__create_aws_host_resolver(ec2_client, config)
        return AWSDockerNodeResolver(aws_host_resolver,
                                     config.aws_docker_host_tag_name,
                                     config.aws_docker_host_tag_value,
                                     config.docker_proxy_username,
                                     config.docker_proxy_password
                                     )

    def __create_config_based_docker_node_resolver(self, config):
        return ConfigBasedDockerNodeResolver(config.docker_nodes)


class DockerNodeResolver(object):
    __metaclass__ = abc.ABCMeta

    @abstractmethod
    def get_docker_nodes(self):
        pass


class ConfigBasedDockerNodeResolver(DockerNodeResolver):

    def __init__(self, docker_nodes):
        self.logger = logging.getLogger(__name__)
        if docker_nodes is None or len(docker_nodes) == 0:
            error_message = "docker_nodes provided was not provided but is mandatory."
            self.logger.error(dict(Message=error_message))
            raise Exception(error_message)
        self.docker_nodes = docker_nodes

    def get_docker_nodes(self):
        return self.docker_nodes


class AWSDockerNodeResolver(DockerNodeResolver):

    logger = logging.getLogger(__name__)

    def __init__(self, aws_host_resolver, aws_docker_host_tag_name, aws_docker_host_tag_value, docker_proxy_username, docker_proxy_password):
        self.aws_host_resolver = aws_host_resolver
        self.aws_docker_host_tag_name = aws_docker_host_tag_name
        self.aws_docker_host_tag_value = aws_docker_host_tag_value
        self.docker_proxy_username = docker_proxy_username
        self.docker_proxy_password = docker_proxy_password

    def get_docker_nodes(self):
        docker_hosts = self.aws_host_resolver.find_running_hosts_private_ip_by_tag(self.aws_docker_host_tag_name,
                                                                                   self.aws_docker_host_tag_value)

        docker_nodes = ["https://{}:{}@{}:9400".format(self.docker_proxy_username, self.docker_proxy_password, docker_host) for docker_host in docker_hosts]
        return docker_nodes

    def __str__(self):
        return str({
            'aws_host_resolver': self.aws_host_resolver,
            'aws_docker_host_tag_name': self.aws_docker_host_tag_name,
            'aws_docker_host_tag_value': self.aws_docker_host_tag_value
        })

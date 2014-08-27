import docker
import socket
from urlparse import urlparse


class Container(dict):
    def __init__(self, docker_connection, node, container_id):
        container_details = docker_connection.inspect_container(container_id)
        self["id"] = container_id
        try:
            self["app"], self["version"] = container_details["Name"][1:].split("_", 1)
        except ValueError:
            self["app"] = container_details["Name"][1:]
            self["version"] = None
        self["node"] = node
        self["running"] = container_details["State"]["Running"]
        self["ip"] = socket.gethostbyname(node)
        self["port"] = int(container_details["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"])
        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(container_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

    def __repr__(self):
        return "<{} {} {} {}>".format(self.app, self.version, self.node, self.id)


class App(list):
    def __init__(self, name, containers=[]):
        self.name = name
        self.extend(containers)

    def __repr__(self):
        return "<{} {} instances>".format(self.name, len(self.containers))


class Connection(object):
    def __init__(self, nodes, verify=False):
        self.node_connections = {}
        for node in nodes:
            address = urlparse(node)
            if address.port:
                docker_conn = docker.Client(base_url="{}://{}:{}".format(address.scheme, address.hostname, address.port),
                     version='1.12', timeout=20)
            else:
                docker_conn = docker.Client(base_url="{}://{}".format(address.scheme, address.hostname),
                     version='1.12', timeout=20)
            docker_conn.verify = verify
            docker_conn.auth = (address.username, address.password)
            self.node_connections[address.hostname] = docker_conn

    def __get_all_containers(self):
        all_containers = []
        for node, node_conn in self.node_connections.items():
            node_containers = node_conn.containers(
                quiet=False, all=True, trunc=False, latest=False,
                since=None, before=None, limit=-1)
            for container in node_containers:
                container_id = container["Id"]
                all_containers.append(self.get_container(node, container_id))
        return all_containers

    def get_all_apps(self):
        all_apps = {}
        for container in self.__get_all_containers():
            try:
                all_apps[container["app"]].append(container)
            except KeyError:
                all_apps[container["app"]] = [container]
        return all_apps

    def get_container(self, node, container_id):
        docker_connection = self.node_connections[node]
        return Container(docker_connection, node, container_id)

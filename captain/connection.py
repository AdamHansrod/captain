import socket
import docker
from urlparse import urlparse
from captain.model import ApplicationInstance


class Connection(object):
    def __init__(self, nodes, api_version, verify=False):
        self.node_connections = {}
        for node in nodes:
            address = urlparse(node)
            docker_conn = self.__get_connection(address, api_version)
            docker_conn.verify = verify
            docker_conn.auth = (address.username, address.password)
            self.node_connections[address.hostname] = docker_conn

    def __get_connection(self, address, api_version):
        if address.port:
            base_url = "{}://{}:{}".format(address.scheme, address.hostname, address.port)
        else:
            base_url = "{}://{}".format(address.scheme, address.hostname)

        return docker.Client(base_url=base_url, version=api_version, timeout=20)

    def __get_all_containers(self):
        all_containers = []
        for node, node_conn in self.node_connections.items():
            node_containers = node_conn.containers(
                quiet=False, all=True, trunc=False, latest=False,
                since=None, before=None, limit=-1)
            for container in node_containers:
                container_id = container["Id"]
                all_containers.append(self.__get_container(node, container_id))
        return all_containers

    def __get_container(self, node, container_id):
        docker_connection = self.node_connections[node]
        inspection_details = docker_connection.inspect_container(container_id)

        try:
            app, version = inspection_details["Name"][1:].split("_", 1)
        except ValueError:
            app, version = inspection_details["Name"][1:], None

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return ApplicationInstance(id=container_id,
                        app=app,
                        version=version,
                        node=node,
                        ip=socket.gethostbyname(node),
                        port=int(inspection_details["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"]),
                        running=inspection_details["State"]["Running"])

    def get_all_apps(self):
        all_apps = {}
        for container in self.__get_all_containers():
            try:
                all_apps[container["app"]].append(container)
            except KeyError:
                all_apps[container["app"]] = [container]
        return all_apps

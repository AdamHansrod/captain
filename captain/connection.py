import docker
from urlparse import urlparse
from captain.model import Instance


class Connection(object):
    def __init__(self, nodes, api_version, verify=False):
        self.node_connections = {}
        for node in nodes:
            address = urlparse(node)
            docker_conn = self.__get_connection(address, api_version)
            docker_conn.verify = verify
            docker_conn.auth = (address.username, address.password)
            self.node_connections[address.hostname] = docker_conn

    def get_instances(self):
        all_containers = []
        for node, node_conn in self.node_connections.items():
            node_containers = node_conn.containers(
                quiet=False, all=False, trunc=False, latest=False,
                since=None, before=None, limit=-1)
            for container in node_containers:
                container_id = container["Id"]
                all_containers.append(self.__get_instance(node, container_id))
        return all_containers

    def stop_instance(self, instance_id):
        instances = self.get_instances()

        for instance in instances:
            if instance["id"] == instance_id:
                docker_hostname = instance["node"]
                docker_container_id = instance_id

                self.node_connections[docker_hostname].stop(docker_container_id)

                try:
                    self.node_connections[docker_hostname].remove_container(docker_container_id, force=True)
                except:
                    pass  # we do not care if removing the container failed

                return True

        return False

    def __get_connection(self, address, api_version):
        if address.port:
            base_url = "{}://{}:{}".format(address.scheme, address.hostname, address.port)
        else:
            base_url = "{}://{}".format(address.scheme, address.hostname)

        return docker.Client(base_url=base_url, version=api_version, timeout=20)

    def __get_instance(self, node, container_id):
        docker_connection = self.node_connections[node]
        inspection_details = docker_connection.inspect_container(container_id)

        try:
            app, version = inspection_details["Name"][1:].split("_", 1)
        except ValueError:
            app, version = inspection_details["Name"][1:], None

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return Instance(id=container_id,
                        app=app,
                        version=version,
                        node=node,
                        port=int(inspection_details["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"]))

import uuid
import docker
from urlparse import urlparse
from captain.model import Instance
import time


class Connection(object):
    def __init__(self, config, verify=False):
        self.config = config

        self.node_connections = {}
        for node in config.docker_nodes:
            address = urlparse(node)
            docker_conn = self.__get_connection(address)
            docker_conn.verify = verify
            docker_conn.auth = (address.username, address.password)
            self.node_connections[address.hostname] = docker_conn

    def get_instances(self):
        instances = []
        for node, node_conn in self.node_connections.items():
            node_containers = node_conn.containers(
                quiet=False, all=True, trunc=False, latest=False,
                since=None, before=None, limit=-1)
            for container in node_containers:
                if container["Status"].startswith("Exited"):
                    now = time.mktime(time.localtime())
                    if now - container["Created"] > self.config.docker_gc_grace_period:
                        node_conn.delete(container["Id"])
                else:
                    node_container = node_conn.inspect_container(container["Id"])
                    instances.append(self.__get_instance(node, node_container))
        return instances

    def start_instance(self, instance):
        app = instance["app"]
        version = instance["version"]
        node = instance["node"]

        environment = instance.get("environment", {})
        environment["PORT"] = "8080"
        environment["SLUG_URL"] = self.config.slug_path.format(app_name=app, app_version=version)

        node_connection = self.node_connections[node]

        # create a container
        container = node_connection.create_container(image=self.config.slug_runner_image,
                                                     command=self.config.slug_runner_command,
                                                     ports=[8080],
                                                     environment=environment,
                                                     detach=True,
                                                     name=app + "_" + version + "_" + str(uuid.uuid4()))

        # start the container
        node_connection.start(container["Id"], port_bindings={8080: None})

        # inspect the container
        # it is important to inspect it *after* starting as before that it doesn't have port info in it)
        container_inspected = node_connection.inspect_container(container["Id"])

        # and return the container converted to an Instance
        return self.__get_instance(node, container_inspected)

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

    def __get_connection(self, address):
        if address.port:
            base_url = "{}://{}:{}".format(address.scheme, address.hostname, address.port)
        else:
            base_url = "{}://{}".format(address.scheme, address.hostname)

        return docker.Client(base_url=base_url, version="1.12", timeout=20)

    def __get_instance(self, node, container):
        try:
            app, version = container["Name"][1:].split("_", 1)
            version = version.split("_")[0]
        except ValueError:
            app, version = container["Name"][1:], None

        environment = {}
        for env_item in container["Config"]["Env"]:
            env_item_key, env_item_value = env_item.split("=", 1)
            if env_item_key not in ['HOME', 'PATH', 'SLUG_URL', 'PORT']:
                environment[env_item_key] = env_item_value

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return Instance(id=container["Id"],
                        app=app,
                        version=version,
                        node=node,
                        port=int(container["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"]),
                        environment=environment)

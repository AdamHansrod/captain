import uuid
import docker
from urlparse import urlparse
from captain import exceptions
import datetime
from requests.exceptions import ConnectionError, Timeout
import struct
import logging


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

    def close(self):
        for node in self.node_connections:
            if node is not None:
                self.node_connections[node].close()

    def get_instances(self, node_filter=None):
        instances = []
        for node, node_conn in self.node_connections.items():
            if node_filter and node != node_filter:
                continue
            try:
                node_containers = node_conn.containers(
                    quiet=False, all=True, trunc=False, latest=False,
                    since=None, before=None, limit=-1)
            except (ConnectionError, Timeout) as e:
                logging.error("Error communication with {}: {}".format(node, e))
                continue
            for container in node_containers:
                if container["Status"].startswith("Exited"):
                    node_container = node_conn.inspect_container(container["Id"])
                    formatted_exit_time = node_container["State"]['FinishedAt']
                    exit_time = datetime.datetime.strptime(formatted_exit_time.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    if (datetime.datetime.now() - exit_time).total_seconds() > self.config.docker_gc_grace_period:
                        node_conn.remove_container(container["Id"])
                elif len(container["Ports"]) == 1 and container["Ports"][0]["PrivatePort"] == 8080:
                    node_container = node_conn.inspect_container(container["Id"])
                    instances.append(self.__get_instance(node, node_container))
        return instances

    def get_node(self, name):
        if name not in self.node_connections:
            raise exceptions.NoSuchNodeException()
        try:
            self.node_connections[name].ping()
            countainer_count = reduce(lambda x, y: x + y["slots"], self.get_instances(node_filter=name), 0)
            return {"id": name,
                    "slots": {
                        "total": self.config.slots_per_node,
                        "used": countainer_count,
                        "free": self.config.slots_per_node - countainer_count},
                    "state": "healthy"}
        except (ConnectionError, Timeout) as e:
            logging.error("Error communication with {}: {}".format(name, e))
            return {"id": name,
                    "slots": {
                        "total": 0,
                        "used": 0,
                        "free": 0},
                    "state": repr(e)}

    def get_nodes(self):
        return [self.get_node(node) for node in self.node_connections.keys()]

    def start_instance(self, app, slug_uri, node, allocated_port=None, environment={}, slots=None):
        environment["PORT"] = "8080"
        environment["SLUG_URL"] = slug_uri

        if not slots:
            slots = self.config.default_slots_per_instance
        if len(self.get_instances(node_filter=node)) + slots > self.config.slots_per_node:
            raise exceptions.NodeOutOfCapacityException()

        node_connection = self.node_connections[node]

        # create a container
        container = node_connection.create_container(image=self.config.slug_runner_image,
                                                     command=self.config.slug_runner_command,
                                                     ports=[8080],
                                                     environment=environment,
                                                     detach=True,
                                                     name=app + "_" + str(uuid.uuid4()),
                                                     cpu_shares=slots,
                                                     mem_limit=self.config.slot_memory_mb * slots * 1024 * 1024)

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

        c = docker.Client(base_url=base_url, version="1.12", timeout=self.config.docker_timeout)

        # This is a hack to allow logs to work thru nginx.
        # It will break bidirectional traffic on .attach but fortunately we don't (yet) use it.
        def __hacked_multiplexed_socket_stream_helper(response):
            c._raise_for_status(response)
            data_buffer = ""
            length = None
            i = response.iter_content(10)
            while True:
                try:
                    data_buffer += i.next()
                except StopIteration:
                    return
                if not length and len(data_buffer) > 8:
                    header = data_buffer[:8]
                    _, length = struct.unpack('>BxxxL', header)

                if length and len(data_buffer[8:]) >= length:
                    yield data_buffer[8:8 + length]
                    data_buffer = data_buffer[8 + length:]
                    length = None
                    continue
        c._multiplexed_socket_stream_helper = __hacked_multiplexed_socket_stream_helper
        return c

    def __get_instance(self, node, container):
        app = container["Name"][1:].split("_")[0]

        environment = {}
        slug_uri = None
        for env_item in container["Config"]["Env"]:
            env_item_key, env_item_value = env_item.split("=", 1)
            if env_item_key not in ['HOME', 'PATH', 'SLUG_URL', 'PORT']:
                environment[env_item_key] = env_item_value
            if env_item_key == 'SLUG_URL':
                slug_uri = env_item_value

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return dict(id=container["Id"],
                    app=app,
                    slug_uri=slug_uri,
                    node=node,
                    port=int(container["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"]),
                    environment=environment,
                    slots=container["Config"]["CpuShares"])

    def get_logs(self, instance_id, follow=False):
        try:
            instance_details = [i for i in self.get_instances() if i["id"] == instance_id][0]
        except IndexError:
            raise exceptions.NoSuchInstanceException()
        node = instance_details["node"]
        node_connection = self.node_connections[node]
        if follow:
            instance_logs = ({"msg": l} for l in node_connection.logs(instance_id, stream=True))
        else:
            instance_logs = ({"msg": "{}\n".format(l)} for l in node_connection.logs(instance_id).split("\n"))
        return instance_logs

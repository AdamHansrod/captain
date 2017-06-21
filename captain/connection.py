import uuid
import docker
from urlparse import urlparse
from captain import exceptions
import datetime
from requests.exceptions import ConnectionError, Timeout
import struct
import logging
from concurrent import futures


class Connection(object):
    def __init__(self, config, aws_host_resolver, verify=False):
        self.config = config
        self.aws_host_resolver = aws_host_resolver

        self.node_connections = {}
        if self.config.aws_docker_host_tag_value is not None:
            docker_hosts = self.aws_host_resolver.find_running_hosts_private_ip_by_tag(self.config.aws_docker_host_tag_name,
                                                                                       self.config.aws_docker_host_tag_value)
            docker_nodes = ["https://{}:9400".format(docker_host)for docker_host in docker_hosts]
        else:
            docker_nodes = config.docker_nodes

        logging.debug("Setting up docker clients for {} configured nodes".format(len(docker_nodes)))

        for node in docker_nodes:
            address = urlparse(node)
            docker_conn = self.__get_connection(address)
            docker_conn.verify = verify
            docker_conn.auth = (address.username, address.password)
            self.node_connections[address.hostname] = docker_conn

    def close(self):
        for node in self.node_connections:
            logging.debug("Closing connection to {}".format(node))
            if node is not None:
                self.node_connections[node].close()

    def get_node_instances(self, node, node_conn):
        node_instances = []
        node_containers = node_conn.containers(
            quiet=False, all=True, trunc=False, latest=False,
            since=None, before=None, limit=-1)
        logging.debug("{} has {} containers".format(node, len(node_containers)))
        for container in node_containers:
            if container["Status"].startswith("Exited"):
                logging.debug("Found exited container on {}".format(node))
                node_container = node_conn.inspect_container(container["Id"])
                formatted_exit_time = node_container["State"]['FinishedAt']
                exit_time = datetime.datetime.strptime(formatted_exit_time.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                if (datetime.datetime.now() - exit_time).total_seconds() > self.config.docker_gc_grace_period:
                    logging.info("Attempting to remove {} from {}".format(container["Id"], node))
                    node_conn.remove_container(container["Id"])
                    logging.info("Removed {} from {}".format(container["Id"], node))
            elif len(container["Ports"]) == 1 and container["Ports"][0]["PrivatePort"] == 8080:
                node_container = node_conn.inspect_container(container["Id"])
                node_instances.append(self.__get_instance(node, node_container))
        return node_instances

    def get_instances(self, node_filter=None):
        instances = []
        filtered_nodes = {}
        for node, node_conn in self.node_connections.items():
            if node_filter and node != node_filter:
                logging.debug("Filtering node {}".format(node))
                continue
            filtered_nodes[node]=node_conn
        with futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_instances = dict((executor.submit(self.get_node_instances, node, node_conn) , node ) for node, node_conn in filtered_nodes.items() )
            for future in futures.as_completed(future_to_instances):
                node = future_to_instances[future]
                if future.exception() is not None:
                    logging.error("Getting instances from {} generated an exception: {}".format(node, type(future.exception())))
                else:
                    instances =  instances + future.result()
                    logging.debug("Get instances for {} found {}".format(node, len(future.result())))
        return instances

    def get_node(self, name):
        if name not in self.node_connections:
            logging.error("Node {} not configured".format(name))
            raise exceptions.NoSuchNodeException()
        try:
            self.node_connections[name].ping()
            countainer_count = reduce(lambda x, y: x + y["slots"], self.get_instances(node_filter=name), 0)
            logging.debug("{} has {} containers".format(name, countainer_count))
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
        nodes = []
        with futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_nodes = dict((executor.submit(self.get_node, node) , node ) for node in self.node_connections.keys() )
            for future in futures.as_completed(future_to_nodes):
                node = future_to_nodes[future]
                if future.exception() is not None:
                    logging.error("Getting details for {} generated an exception: {}".format(node, type(future.exception())))
                else:
                    nodes =  nodes + [future.result()]
                    logging.debug("Got details for {}".format(node))
        return nodes

    def start_instance(self, app, slug_uri, node, allocated_port=None, environment={}, slots=None, hostname=None):
        environment["PORT"] = "8080"
        environment["SLUG_URL"] = slug_uri

        if not slots:
            logging.info("Setting default slots for {}".format(app))
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
                                                     hostname=hostname,
                                                     name=app + "_" + str(uuid.uuid4()),
                                                     cpu_shares=slots,
                                                     mem_limit=self.config.slot_memory_mb * slots * 1024 * 1024)
        logging.debug("Created container for {} on {}".format(app, node))

        # start the container
        node_connection.start(container["Id"], port_bindings={8080: None})
        logging.debug("Started container for {} on {}".format(app, node))

        # inspect the container
        # it is important to inspect it *after* starting as before that it doesn't have port info in it)
        container_inspected = node_connection.inspect_container(container["Id"])
        logging.info("Finished starting container for app {} on {}".format(app, node))

        # and return the container converted to an Instance
        return self.__get_instance(node, container_inspected)

    def stop_instance(self, instance_id):
        instances = self.get_instances()

        for instance in instances:
            if instance["id"] == instance_id:
                docker_hostname = instance["node"]
                docker_container_id = instance_id
                logging.debug("Stopping container {} on {}".format(docker_container_id, docker_hostname))
                self.node_connections[docker_hostname].stop(docker_container_id)
                logging.info("Stopped container {} on {}".format(docker_container_id, docker_hostname))

                try:
                    self.node_connections[docker_hostname].remove_container(docker_container_id, force=True)
                    logging.debug("Removed container {} on {}".format(docker_container_id, docker_hostname))
                except:
                    logging.warn("Failed to remove container {} on {}".format(docker_container_id, docker_hostname))
                    pass  # we do not care if removing the container failed

                return True

        return False

    def __get_connection(self, address):
        if address.port:
            base_url = "{}://{}:{}".format(address.scheme, address.hostname, address.port)
        else:
            base_url = "{}://{}".format(address.scheme, address.hostname)

        c = docker.Client(base_url=base_url, version="1.12", timeout=self.config.docker_timeout)
        logging.debug("Docker client created for {}".format(address.hostname))
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
        logging.debug("App name is {}".format(app))
        environment = {}
        slug_uri = None
        for env_item in container["Config"]["Env"]:
            env_item_key, env_item_value = env_item.split("=", 1)
            if env_item_key not in ['HOME', 'PATH', 'SLUG_URL', 'PORT']:
                environment[env_item_key] = env_item_value
            else:
                logging.debug("Skipping {} from environment".format(env_item_key))
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

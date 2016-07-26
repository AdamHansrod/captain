import uuid
import docker
from urlparse import urlparse
from captain import exceptions
# futures and datetime together do weird things
#  https://mail.python.org/pipermail/python-list/2012-December/650103.html
import datetime, _strptime
from requests.exceptions import ConnectionError, Timeout
import struct
import logging
import logging.config
from concurrent import futures
from backports.functools_lru_cache import lru_cache as lru_cache
from collections import Counter

lru_cache_size = 1024

logging.config.fileConfig("logging.conf")
logger = logging.getLogger('connection')


class Connection(object):
    def __init__(self, config, verify=False):
        self.config = config

        self.node_connections = {}
        logger.debug(dict(message="Setting up docker clients for {} configured nodes".format(len(config.docker_nodes))))
        for node in config.docker_nodes:
            try:
                address = urlparse(node)
                docker_conn = self.__get_connection(address)
                docker_conn.verify = verify
                docker_conn.auth = (address.username, address.password)
                self.node_connections[address.hostname] = docker_conn
            except Exception:
                logger.exception('Failed to add node from config: {}'.format(node))
        logger.debug(dict(message='Nodes configured: {}'.format(self.node_connections)))

    def close(self):
        for node in self.node_connections:
            logger.debug(dict(message="Closing connection to {}".format(node)))
            if node is not None:
                self.node_connections[node].close()

    @lru_cache(maxsize=lru_cache_size)
    def _get_lru_instance_details(self, node, container_id, container_status, public_port):
        logger.debug(dict(message="Cache miss on node {} container {}".format(node, container_id)))
        node_conn = self.node_connections[node]
        node_container = node_conn.inspect_container(container_id)
        return node_container

    def get_node_instances(self, node):
        node_conn = self.node_connections[node]
        node_instances = []
        node_containers = node_conn.containers(
            quiet=False, all=True, trunc=False, latest=False,
            since=None, before=None, limit=-1)
        logger.debug(dict(message="{} has {} containers".format(node, len(node_containers))))
        exited_container_count = 0
        deleted_container_count = 0
        for container in node_containers:
            # Grab the first part of State to give uniqueness of container and state for the lru_cache
            full_container_status = container["Status"]
            container_status = full_container_status.split()[0] if full_container_status else full_container_status

            if not container["Status"].startswith("Up "):
                exited_container_count += 1
                logger.debug(dict(message="Found exited container on {}".format(node)))
                node_container = self._get_lru_instance_details(node, container["Id"], container_status, 0)

                formatted_create_time = node_container["Created"]
                created_time = datetime.datetime.strptime(formatted_create_time.rstrip("Z").split('.')[0], '%Y-%m-%dT%H:%M:%S')
                formatted_exit_time = node_container["State"]['FinishedAt']
                exit_time = datetime.datetime.strptime(formatted_exit_time.rstrip("Z").split('.')[0], '%Y-%m-%dT%H:%M:%S')
                if (datetime.datetime.now() - created_time).total_seconds() < self.config.docker_gc_grace_period or \
                   (datetime.datetime.now() - exit_time).total_seconds() < self.config.docker_gc_grace_period:
                    logger.debug(dict(message="Exited container {} on {} not older than gc period, ignoring".format(container["Id"], node)))
                else:
                    try:
                        node_conn.remove_container(container["Id"])
                        deleted_container_count += 1
                        logger.warn(dict(message="Exited container {} on {} with exit time at {} older than gc period, removed".format(container["Id"], node, formatted_exit_time)))
                    except docker.errors.APIError as e:
                        if '404 Client Error' in e.message:
                            logger.info(dict(message='Container already removed: {}'.format(container["Id"])))
                        else:
                            raise
            elif "Ports" in container and len(container["Ports"]) == 1 and container["Ports"][0]["PrivatePort"] == 8080:
                public_port = container["Ports"][0]["PublicPort"]
                try:
                    node_container = self._get_lru_instance_details(node, container["Id"], container_status, public_port)
                    node_instances.append(self.__get_instance(node, node_container))
                except docker.errors.APIError as e:
                    if '404 Client Error' in e.message:
                        logger.info(dict(message='Container was deleted before being inspected: {}'.format(container["Id"])))
                    else:
                        raise
        logger.debug('Found {} exited containers, {} were deleted'.format(exited_container_count, deleted_container_count))
        return node_instances

    def get_instances(self, node_filter=None):
        instances = []
        filtered_nodes = {}
        for node, node_conn in self.node_connections.items():
            if node_filter and node != node_filter:
                logger.debug(dict(message="Filtering node {}".format(node)))
                continue
            filtered_nodes[node] = node_conn
        with futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_instances = dict((executor.submit(self.get_node_instances, node), node) for node, node_conn in filtered_nodes.items())
            for future in futures.as_completed(future_to_instances):
                node = future_to_instances[future]
                try:
                    instances = instances + future.result()
                    logger.debug(dict(message="Get instances for {} found {}".format(node, len(future.result()))))
                except Exception as e:
                    logger.error(dict(message="Getting instances from {} generated an exception: {}".format(node, e)))
        return instances

    def get_node(self, name):
        if name not in self.node_connections:
            logger.error(dict(message="Node {} not configured".format(name)))
            raise exceptions.NoSuchNodeException()
        try:
            self.node_connections[name].ping()
            countainer_count = reduce(lambda x, y: x + y["slots"], self.get_instances(node_filter=name), 0)
            logger.debug(dict(message="{} has {} containers".format(name, countainer_count)))
            return {"id": name,
                    "slots": {
                        "total": self.config.slots_per_node,
                        "used": countainer_count,
                        "free": self.config.slots_per_node - countainer_count},
                    "state": "healthy"}
        except (ConnectionError, Timeout) as e:
            logger.error(dict(message="Error communication with {}: {}".format(name, e)))
            return {"id": name,
                    "slots": {
                        "total": 0,
                        "used": 0,
                        "free": 0},
                    "state": repr(e)}

    def get_nodes(self):
        nodes = []
        with futures.ThreadPoolExecutor(max_workers=8) as executor:
            future_to_nodes = dict((executor.submit(self.get_node, node), node) for node in self.node_connections.keys())
            for future in futures.as_completed(future_to_nodes):
                node = future_to_nodes[future]
                if future.exception() is not None:
                    logger.error(dict(message="Getting details for {} generated an exception: {}".format(node, type(future.exception()))))
                else:
                    nodes = nodes + [future.result()]
                    logger.debug(dict(message="Got details for {}".format(node)))
        return nodes

    def get_instance_summary(self):
        summary = {"total_instances": 0}
        apps = Counter()
        logger.debug(dict(message="Getting instances to generate summary"))
        instances = self.get_instances()
        for instance in instances:
            summary["total_instances"] += 1
            apps[instance["app"]] += 1
            logger.debug(dict(message="Incrementing {} to {}".format(instance["app"], apps[instance["app"]])))
        summary.update({"apps": dict(apps)})
        logger.debug(dict(message="Returning summary {}".format(summary)))
        return summary

    def start_instance(self, app, slug_uri, node, allocated_port=None, environment={}, slots=None, hostname=None, slug_runner_version=None):
        environment["PORT"] = "8080"
        environment["SLUG_URL"] = slug_uri

        if not slots:
            logger.info(dict(message="Setting default slots for {}".format(app)))
            slots = self.config.default_slots_per_instance
        current_slot_count = sum([
            instance["slots"] for instance in self.get_instances()
            if instance['node'] == node])
        if current_slot_count + slots > self.config.slots_per_node:
            raise exceptions.NodeOutOfCapacityException()

        node_connection = self.node_connections[node]

        # Use the version from the api parameter if it's set, otherwise use the version from config
        if slug_runner_version is None:
            slug_runner_versioned_image = "{}:{}".format(self.config.slug_runner_image, self.config.slug_runner_version)
        else:
            slug_runner_versioned_image = "{}:{}".format(self.config.slug_runner_image, slug_runner_version)

        # create a container
        container = node_connection.create_container(image=slug_runner_versioned_image,
                                                     command=self.config.slug_runner_command,
                                                     ports=[8080],
                                                     environment=environment,
                                                     detach=True,
                                                     hostname=hostname,
                                                     name=app + "_" + str(uuid.uuid4()),
                                                     cpu_shares=slots,
                                                     mem_limit=self.config.slot_memory_mb * slots * 1024 * 1024)
        logger.debug(dict(message="Created container for {} on {}".format(app, node)))

        # start the container
        node_connection.start(container["Id"], port_bindings={8080: None})
        logger.debug(dict(message="Started container for {} on {}".format(app, node)))

        # inspect the container
        # it is important to inspect it *after* starting as before that it doesn't have port info in it)
        container_inspected = node_connection.inspect_container(container["Id"])
        logger.info(dict(message="Finished starting container for app {} on {}".format(app, node)))

        # and return the container converted to an Instance
        return self.__get_instance(node, container_inspected)

    def stop_instance(self, instance_id):
        instances = self.get_instances()

        for instance in instances:
            if instance["id"] == instance_id:
                docker_hostname = instance["node"]
                docker_container_id = instance_id
                logger.debug(dict(message="Stopping container {} on {}".format(docker_container_id, docker_hostname)))
                self.node_connections[docker_hostname].stop(docker_container_id)
                logger.info(dict(message="Stopped container {} on {}".format(docker_container_id, docker_hostname)))

                try:
                    self.node_connections[docker_hostname].remove_container(docker_container_id, force=True)
                    logger.info(dict(message="Removed container {} on {}".format(docker_container_id, docker_hostname)))
                except:
                    logger.warn(dict(message="Failed to remove container {} on {}".format(docker_container_id, docker_hostname)))
                    pass  # we do not care if removing the container failed

                return True

        return False

    def __get_connection(self, address):
        if address.port:
            base_url = "{}://{}:{}".format(address.scheme, address.hostname, address.port)
        else:
            base_url = "{}://{}".format(address.scheme, address.hostname)

        c = docker.Client(base_url=base_url, version="1.12", timeout=self.config.docker_timeout)
        logger.debug(dict(message="Docker client created for {}".format(address.hostname)))

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
        logger.debug(dict(message="getting instance details", microservice="App name is {}".format(app)))
        environment = {}
        slug_uri = None
        for env_item in container["Config"]["Env"]:
            env_item_key, env_item_value = env_item.split("=", 1)
            if env_item_key not in ['HOME', 'PATH', 'SLUG_URL', 'PORT']:
                environment[env_item_key] = env_item_value
            else:
                logger.debug(dict(message="Skipping {} from environment".format(env_item_key)))
            if env_item_key == 'SLUG_URL':
                slug_uri = env_item_value

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return dict(id=container["Id"],
                    app=app,
                    slug_uri=slug_uri,
                    node=node,
                    port=int(container["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]),
                    environment=environment,
                    slots=container["Config"]["CpuShares"],
                    hostname=container["Config"]["Hostname"])

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

import uuid
import docker
from urlparse import urlparse
from captain.model import Instance


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
                quiet=False, all=False, trunc=False, latest=False,
                since=None, before=None, limit=-1)
            for container in node_containers:
                node_container = node_conn.inspect_container(container["Id"])
                instances.append(self.__get_instance(node, node_container))
        return instances

    def start_instance(self, instance):
        app = instance["app"]
        version = instance["version"]
        node = instance["node"]

        node_connection = self.node_connections[node]

        unique_identifier = str(uuid.uuid4())
        slug_url = self.slug_path.format(app_name=app, app_version=version)
        config = "-Dgovuk-tax.Prod.services.ida.tokenapi.pathBase=https://ida-internal.tax.service.gov.uk -Dgovuk-tax.Prod.services.ida.tokenapi.username=X6WWYmqdewFIKngwMLD1mQ== -Drun.mode=Prod -Dgovuk-tax.Prod.services.ida.tokenapi.password=Ut3GPyy3hbTk6wpgvMB2WtTq3fuGuj2OVdiKKAidCxc= -Dsso.encryption.key=+Kn8pcuRGnFY5+9aaOgC4g== -Dgovuk-tax.Prod.externalLinks.servicesUrl=https://secure.hmce.gov.uk -Dgovuk-tax.Prod.platform.frontend.host=web-qa.tax.service.gov.uk -Dgovuk-tax.Prod.externalLinks.customsUrl=https://customs.hmrc.gov.uk -Dapplication.secret=6FsmK_gRYea=33xnBx6koN7BUi7TT`rZWUv`dPJFkL_01EE>hssT4;A^;EW>>u5@ -Dapplication.log=INFO -Dlogger.resource=/application-json-logger.xml -Dhttp.port=8080 -Dgovuk-tax.Prod.google-analytics.token=UA-43414424-4 -Dgovuk-tax.Prod.platform.frontend.protocol=https -Dcookie.encryption.key=isoidInFoiIHNCOSJRCC2D== -Dgovuk-tax.Prod.services.ida.tokenapi.tokenRequired=false"
        java_opts = "-Xmx256m -Xms256m"

        # create a container
        container = node_connection.create_container(image=self.config.slug_runner_image,
                                                     command=self.config.slug_runner_command,
                                                     ports=[8080],
                                                     environment={"PORT": "8080",
                                                                  "SLUG_URL": slug_url,
                                                                  "HMRC_CONFIG": config,
                                                                  "JAVA_OPTS": java_opts}, detach=True,
                                                     name=app + "_" + version + "_" + unique_identifier)

        # start it
        node_connection.start(container["Id"], port_bindings={8080: None})

        # inspect the container (after starting it, important! before it it doesn't have port info in it)
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

        # Docker breaks stuff, when talking to > 1.1.1 this might be the place to find the port on stopped containers.
        # self.port = int(inspection_details["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"])

        return Instance(id=container["Id"],
                        app=app,
                        version=version,
                        node=node,
                        port=int(container["HostConfig"]["PortBindings"]["8080/tcp"][0]["HostPort"]))

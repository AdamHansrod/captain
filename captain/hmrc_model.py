import socket


class Instance(dict):
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


class Application(list):
    def __init__(self, name, instances=[]):
        self.name = name
        self.extend(instances)

    def __repr__(self):
        return "<{} {} instances>".format(self.name, len(self.containers))

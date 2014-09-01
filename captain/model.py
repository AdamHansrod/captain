class ApplicationInstance(dict):
    def __init__(self, id, app, version, node, ip, port, running):
        self["id"] = id
        self["app"] = app
        self["version"] = version
        self["node"] = node
        self["ip"] = ip
        self["port"] = port
        self["running"] = running

    def __repr__(self):
        return "<{} {} @{}:{} ({})>".format(self.app, self.version, self.node, self.port, self.id)


class Application(list):
    def __init__(self, name, instances=[]):
        self.name = name
        self.extend(instances)

    def __repr__(self):
        return "<{} (instances: {})>".format(self.name, len(self.instances))

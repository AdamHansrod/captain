class Instance(dict):
    def __init__(self, id, app, version, node, port, environment):
        self["id"] = id
        self["app"] = app
        self["version"] = version
        self["node"] = node
        self["port"] = port
        self["environment"] = environment

    def __repr__(self):
        return "<{} {} @{}:{} ({})>".format(self.app, self.version, self.node, self.port, self.id)

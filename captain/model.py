class Instance(dict):
    def __init__(self, id, app, version, node, port):
        self["id"] = id
        self["app"] = app
        self["version"] = version
        self["node"] = node
        self["port"] = port

    def __repr__(self):
        return "<{} {} @{}:{} ({})>".format(self.app, self.version, self.node, self.port, self.id)

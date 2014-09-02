class Instance(dict):
    def __init__(self, id, app, version, node, address, port):
        self["id"] = id
        self["app"] = app
        self["version"] = version
        self["node"] = node
        self["address"] = address
        self["port"] = port

    def __repr__(self):
        return "<{} {} @{}:{} ({}/{})>".format(self.app, self.version, self.address, self.port, self.node, self.id)

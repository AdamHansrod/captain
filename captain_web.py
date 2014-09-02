from flask import Flask, g, abort
from flask.ext import restful
import os
from captain.connection import Connection

app = Flask(__name__)
app.debug = True
api = restful.Api(app, catch_all_404s=True)

import logging
stream_handler = logging.StreamHandler()
app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

DOCKER_NODES = os.getenv("DOCKER_NODES", "http://localhost:5000").split(",")
DOCKER_API_VERSION = os.getenv("DOCKER_API_VERSION")

@app.before_request
def before_request():
    g.captain_conn = Connection(nodes=DOCKER_NODES, api_version=DOCKER_API_VERSION)


class RestInstances(restful.Resource):
    def get(self):
        return g.captain_conn.get_instances()


class RestInstance(restful.Resource):
    def get(self, instance_id):
        try:
            return filter(lambda instance: instance["id"] == instance_id, g.captain_conn.get_instances())[0]
        except KeyError:
            abort(404)

    def delete(self, instance_id):
        g.captain_conn.stop_instance(instance_id)
        return '', 204

api.add_resource(RestInstances, '/instances/')
api.add_resource(RestInstance, '/instances/<string:instance_id>')

if __name__ == '__main__':
    app.run(debug=True, port=1234)

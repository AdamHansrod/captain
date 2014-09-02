from flask import Flask, g, abort, request, redirect, url_for
from flask.ext import restful
import os
from captain.config import Config
from captain.connection import Connection

app = Flask(__name__)
app.debug = True
api = restful.Api(app, catch_all_404s=True)

import logging
stream_handler = logging.StreamHandler()
app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

DOCKER_NODES = os.getenv("DOCKER_NODES", "http://localhost:5000").split(",")

@app.before_request
def before_request():
    g.captain_conn = Connection(Config())


class RestInstances(restful.Resource):
    def get(self):
        return g.captain_conn.get_instances()

    def post(self):
        if not request.json:
            abort(400)

        instance_request = request.json
        instance_response = g.captain_conn.start_instance(instance_request)

        return redirect('/instances/' + instance_response["id"], code=201)

class RestInstance(restful.Resource):
    def get(self, instance_id):
        try:
            return filter(lambda instance: instance["id"] == instance_id, g.captain_conn.get_instances())[0]
        except KeyError:
            abort(404)

    def delete(self, instance_id):
        stopped = g.captain_conn.stop_instance(instance_id)

        if stopped:
            return '', 204
        else:
            abort(404)

api.add_resource(RestInstances, '/instances/')
api.add_resource(RestInstance, '/instances/<string:instance_id>')

if __name__ == '__main__':
    app.run(debug=True, port=1234)

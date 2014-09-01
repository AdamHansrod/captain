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


class RestApplications(restful.Resource):
    def get(self):
        return g.captain_conn.get_applications()


class RestApplication(restful.Resource):
    def get(self, application_name):
        try:
            return g.captain_conn.get_applications()[application_name]
        except KeyError:
            abort(404)

    def delete(self, application_name):
        g.captain_conn.stop_application(application_name)
        return '', 204


class RestApplicationInstance(restful.Resource):
    def get(self, application_name, application_instance_id):
        try:
            return filter(lambda application_instance: application_instance["id"] == application_instance_id, g.captain_conn.get_applications()[application_name])[0]
        except KeyError:
            abort(404)

    def delete(self, application_name, application_instance_id):
        g.captain_conn.stop_application_instance(application_name, application_instance_id)
        return '', 204

api.add_resource(RestApplications, '/apps/')
api.add_resource(RestApplication, '/apps/<string:application_name>')
api.add_resource(RestApplicationInstance, '/apps/<string:application_name>/instances/<string:application_instance_id>')

if __name__ == '__main__':
    app.run(debug=True, port=1234)

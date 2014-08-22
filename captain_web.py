from flask import Flask, g, abort
from flask.ext import restful
import captain
import os

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
    g.captain_conn = captain.Connection(nodes=DOCKER_NODES)

class Containers(restful.Resource):
    def get(self):
        return g.captain_conn.get_all_apps()

class Container(restful.Resource):
    def get(self, app_id):
        try:
            return g.captain_conn.get_all_apps()[app_id]
        except KeyError:
            abort(404)

api.add_resource(Containers, '/apps/')
api.add_resource(Container, '/apps/<string:app_id>')

if __name__ == '__main__':
    app.run(debug=True, port=1234)

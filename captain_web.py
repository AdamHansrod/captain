import boto3
from flask import Flask, g, request, redirect, Response
from flask.ext import restful
from flask.ext.restful import reqparse

from captain.aws_host_resolver import AWSHostResolver
from captain.config import Config
from captain.connection import Connection
from captain import exceptions
import socket
import json

app = Flask(__name__)
app.debug = True
api = restful.Api(app, catch_all_404s=True)

import logging
stream_handler = logging.StreamHandler()
app.logger.addHandler(stream_handler)
app.logger.setLevel(logging.INFO)

ec2_client = boto3.client('ec2')
aws_host_resolver = AWSHostResolver(ec2_client)
config = Config()
try:
    app.logger.setLevel(config.logging_level)
    app.logger.info("Logging level set to {}".format(config.logging_level))
except ValueError:
    app.logger.error("Unable to configured specified logging level, '{}' is an invalid value.".format(config.logging_level))


@app.before_request
def before_request():
    g.captain_conn = Connection(config, aws_host_resolver)


@app.teardown_appcontext
def teardown_request(exception):
    docker_connection = getattr(g, 'captain_conn', None)
    if docker_connection is not None:
        docker_connection.close()


class RestInstances(restful.Resource):
    def get(self):
        return g.captain_conn.get_instances()

    def post(self):
        if not request.json:
            restful.abort(400)

        instance_request = request.json
        try:
            instance_response = g.captain_conn.start_instance(**instance_request)
        except exceptions.NodeOutOfCapacityException:
            restful.abort(503,
                          message="There aren't enough free slots on {} to service your request".format(instance_request["node"]))

        return instance_response, 201


class RestInstance(restful.Resource):
    def get(self, instance_id):
        try:
            return filter(lambda instance: instance["id"] == instance_id, g.captain_conn.get_instances())[0]
        except IndexError:
            restful.abort(404)

    def delete(self, instance_id):
        if instance_id.startswith(socket.gethostname()):
            # My hostname is the short container ID.
            # I've just been asked to kill myself.
            #   I'll send a redirect to try again instead of committing suicide.
            return redirect(
                api.url_for(
                    self,
                    instance_id=instance_id,
                ), code=307)

        stopped = g.captain_conn.stop_instance(instance_id)

        if stopped:
            return '', 204
        else:
            restful.abort(404)


class RestInstanceLogs(restful.Resource):
    def get(self, instance_id):
        parser = reqparse.RequestParser()
        parser.add_argument('follow', type=int, location='args', default=0)
        args = parser.parse_args()

        try:
            r = Response(("{}\n".format(json.dumps(l)) for l in g.captain_conn.get_logs(instance_id, follow=args.follow == 1)), mimetype='application/jsonstream')
            return r
        except exceptions.NoSuchInstanceException:
            restful.abort(404)


class RestPing(restful.Resource):
    def get(self):
        Response("{}", mimetype='application/json')


api.add_resource(RestInstances, '/instances/')
api.add_resource(RestInstance, '/instances/<string:instance_id>')
api.add_resource(RestInstanceLogs, '/instances/<string:instance_id>/logs')
api.add_resource(RestPing, '/ping/ping')


class RestNodes(restful.Resource):
    def get(self):
        return g.captain_conn.get_nodes()


class RestNode(restful.Resource):
    def get(self, node_id):
        try:
            return g.captain_conn.get_node(node_id)
        except exceptions.NoSuchNodeException:
            restful.abort(404)

api.add_resource(RestNodes, '/nodes/')
api.add_resource(RestNode, '/nodes/<string:node_id>')

if __name__ == '__main__':
    app.run(debug=True, port=1234)

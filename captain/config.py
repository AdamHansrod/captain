import os


class Config(object):
    def __init__(self):
        self.docker_nodes = os.getenv("DOCKER_NODES", "http://localhost:5000").split(",")

        self.slug_path = os.getenv("SLUG_PATH")
        if self.slug_path is None:
            raise Exception("SLUG_PATH should be specified")

        self.slug_runner_command = os.getenv("SLUG_RUNNER_COMMAND")
        if self.slug_runner_command is None:
            raise Exception("SLUG_RUNNER_COMMAND should be specified")

        self.slug_runner_image = os.getenv("SLUG_RUNNER_IMAGE")
        if self.slug_runner_image is None:
            raise Exception("SLUG_RUNNER_IMAGE should be specified")

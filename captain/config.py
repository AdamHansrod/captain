import os


class Config(object):
    def __init__(self):
        self.docker_nodes = os.getenv("DOCKER_NODES", "http://localhost:5000").split(",")

        self.slug_path = "https://webstore.tax.service.gov.uk/{app_name}/{app_name}_{app_version}.tgz"
        self.slug_runner_command = "start web"
        self.slug_runner_image = "hmrc/slugrunner"

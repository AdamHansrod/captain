import os


class Config(object):
    def __init__(self):

        self.docker_nodes = []
        docker_nodes_string = os.getenv("DOCKER_NODES", None)
        if docker_nodes_string is not None:
                self.docker_nodes = docker_nodes_string.split(",")
        self.aws_call_interval_secs = int(os.getenv("AWS_CALL_INTERVAL_SECS", "60"))
        self.aws_docker_host_tag_name = os.getenv("AWS_DOCKER_HOST_TAG_NAME", "role")
        self.aws_docker_host_tag_value = os.getenv("AWS_DOCKER_HOST_TAG_VALUE")
        self.docker_proxy_username = os.getenv("DOCKER_PROXY_USERNAME")
        self.docker_proxy_password = os.getenv("DOCKER_PROXY_PASSWORD")
        if len(self.docker_nodes) > 0 and self.aws_docker_host_tag_value is not None:
            raise Exception("DOCKER_NODES and AWS_DOCKER_HOST_TAG_VALUE are mutually exclusive")

        if self.aws_docker_host_tag_value and self.docker_proxy_username and self.docker_proxy_password :
            raise Exception("If AWS_DOCKER_HOST_TAG_VALUE is specified then "
                            "DOCKER_PROXY_USERNAME and DOCKER_PROXY_PASSWORD should also be.")

        self.docker_gc_grace_period = int(os.getenv("DOCKER_GC_GRACE_PERIOD", "86400"))
        self.docker_timeout = int(os.getenv("DOCKER_TIMEOUT", "15"))

        # Assumed 16GB RAM, 128MB per container with 2-3GB reserved for OS
        self.slots_per_node = int(os.getenv("SLOTS_PER_NODE", "110"))
        self.slot_memory_mb = int(os.getenv("SLOT_MEMORY_MB", "128"))
        self.default_slots_per_instance = int(os.getenv("DEFAULT_SLOTS_PER_INSTANCE", "2"))

        self.slug_runner_command = os.getenv("SLUG_RUNNER_COMMAND")
        if self.slug_runner_command is None:
            raise Exception("SLUG_RUNNER_COMMAND must be specified")

        self.slug_runner_image = os.getenv("SLUG_RUNNER_IMAGE")
        self.slug_runner_version = os.getenv("SLUG_RUNNER_VERSION", "0.0.0")
        if self.slug_runner_image is None:
            raise Exception("SLUG_RUNNER_IMAGE must be specified")

        self.log_config_file_path = os.getenv("LOG_CONFIG_FILE_PATH", "logging.conf")

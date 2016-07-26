import os


class Config(object):
    def __init__(self):
        self.docker_nodes = os.getenv("DOCKER_NODES", "http://localhost:5000").split(",")
        self.docker_gc_grace_period = int(os.getenv("DOCKER_GC_GRACE_PERIOD", "86400"))
        self.docker_timeout = int(os.getenv("DOCKER_TIMEOUT", "15"))

        # Assumed 16GB RAM, 128MB per container with 2-3GB reserved for OS
        self.slots_per_node = int(os.getenv("SLOTS_PER_NODE", "110"))
        self.slot_memory_mb = int(os.getenv("SLOT_MEMORY_MB", "128"))
        self.default_slots_per_instance = int(os.getenv("DEFAULT_SLOTS_PER_INSTANCE", "2"))

        self.slug_runner_command = os.getenv("SLUG_RUNNER_COMMAND")
        if self.slug_runner_command is None:
            raise Exception("SLUG_RUNNER_COMMAND should be specified")

        self.slug_runner_image = os.getenv("SLUG_RUNNER_IMAGE")
        self.slug_runner_version = os.getenv("SLUG_RUNNER_VERSION", "0.0.0")
        if self.slug_runner_image is None:
            raise Exception("SLUG_RUNNER_IMAGE should be specified")

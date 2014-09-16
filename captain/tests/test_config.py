import unittest
import mock
from nose.tools import raises
from captain.config import Config


class TestConfig(unittest.TestCase):

    DOCKER_NODE_1 = "http://some-node-1:5000"
    DOCKER_NODE_2 = "http://some-node-2:5000"
    SLUG_PATH = "http://some/slug/path"
    SLUG_RUNNER_COMMAND = "some command"
    SLUG_RUNNER_IMAGE = "runner/image"
    DOCKER_GC_GRACE_PERIOD = "100"
    SLOTS_PER_NODE = "10"
    SLOT_MEMORY_MB = "128"
    DEFAULT_SLOTS_PER_INSTANCE = "2"

    @mock.patch("os.getenv")
    def test_gets_config_from_environment_properties(self, mock_getenv):
        # given
        environment = {
            "DOCKER_NODES": "{},{}".format(self.DOCKER_NODE_1, self.DOCKER_NODE_2),
            "SLUG_PATH": self.SLUG_PATH,
            "SLUG_RUNNER_COMMAND": self.SLUG_RUNNER_COMMAND,
            "SLUG_RUNNER_IMAGE": self.SLUG_RUNNER_IMAGE,
            "DOCKER_GC_GRACE_PERIOD": self.DOCKER_GC_GRACE_PERIOD,
            "SLOTS_PER_NODE": self.SLOTS_PER_NODE,
            "SLOT_MEMORY_MB": self.SLOT_MEMORY_MB,
            "DEFAULT_SLOTS_PER_INSTANCE": self.DEFAULT_SLOTS_PER_INSTANCE
        }
        self.mock_environment(mock_getenv, environment)

        # when
        config = Config()

        # then
        self.assertEqual(config.docker_nodes, [self.DOCKER_NODE_1, self.DOCKER_NODE_2])
        self.assertEqual(config.slug_path, self.SLUG_PATH)
        self.assertEqual(config.slug_runner_command, self.SLUG_RUNNER_COMMAND)
        self.assertEqual(config.slug_runner_image, self.SLUG_RUNNER_IMAGE)
        self.assertEqual(config.docker_gc_grace_period, int(self.DOCKER_GC_GRACE_PERIOD))

        self.assertEqual(config.slots_per_node, int(self.SLOTS_PER_NODE))
        self.assertEqual(config.slot_memory_mb, int(self.SLOT_MEMORY_MB))
        self.assertEqual(config.default_slots_per_instance, int(self.DEFAULT_SLOTS_PER_INSTANCE))

    @mock.patch("os.getenv")
    def test_defaults(self, mock_getenv):
        # given
        environment = {
            "SLUG_PATH": self.SLUG_PATH,
            "SLUG_RUNNER_COMMAND": self.SLUG_RUNNER_COMMAND,
            "SLUG_RUNNER_IMAGE": self.SLUG_RUNNER_IMAGE
        }
        self.mock_environment(mock_getenv, environment)

        # when
        config = Config()

        # then
        self.assertEqual(config.docker_nodes, ["http://localhost:5000"])
        self.assertEqual(config.slug_path, self.SLUG_PATH)
        self.assertEqual(config.slug_runner_command, self.SLUG_RUNNER_COMMAND)
        self.assertEqual(config.slug_runner_image, self.SLUG_RUNNER_IMAGE)

        self.assertEqual(config.slug_path, self.SLUG_PATH)
        self.assertEqual(config.slug_runner_command, self.SLUG_RUNNER_COMMAND)
        self.assertEqual(config.slug_runner_image, self.SLUG_RUNNER_IMAGE)
        self.assertEqual(config.docker_gc_grace_period, 86400)

        self.assertEqual(config.slots_per_node, 110)
        self.assertEqual(config.slot_memory_mb, int(self.SLOT_MEMORY_MB))
        self.assertEqual(config.default_slots_per_instance, int(self.DEFAULT_SLOTS_PER_INSTANCE))

    @mock.patch("os.getenv")
    @raises(Exception)
    def test_fails_when_no_slug_path_specified(self, mock_getenv):
        # given
        environment = {
            "DOCKER_NODES": "{},{}".format(self.DOCKER_NODE_1, self.DOCKER_NODE_2),
            "SLUG_RUNNER_COMMAND": self.SLUG_RUNNER_COMMAND,
            "SLUG_RUNNER_IMAGE": self.SLUG_RUNNER_IMAGE
        }
        self.mock_environment(mock_getenv, environment)

        # when
        Config()

        # then
        # (exception expected - see @raises)

    @mock.patch("os.getenv")
    @raises(Exception)
    def test_fails_when_no_slug_runner_command_specified(self, mock_getenv):
        # given
        environment = {
            "DOCKER_NODES": "{},{}".format(self.DOCKER_NODE_1, self.DOCKER_NODE_2),
            "SLUG_PATH": self.SLUG_PATH,
            "SLUG_RUNNER_IMAGE": self.SLUG_RUNNER_IMAGE
        }
        self.mock_environment(mock_getenv, environment)

        # when
        Config()

        # then
        # (exception expected - see @raises)

    @mock.patch("os.getenv")
    @raises(Exception)
    def test_fails_when_no_slug_runner_image_specified(self, mock_getenv):
        # given
        environment = {
            "DOCKER_NODES": "{},{}".format(self.DOCKER_NODE_1, self.DOCKER_NODE_2),
            "SLUG_PATH": self.SLUG_PATH,
            "SLUG_RUNNER_COMMAND": self.SLUG_RUNNER_COMMAND,
        }
        self.mock_environment(mock_getenv, environment)

        # when
        Config()

        # then
        # (exception expected - see @raises)

    def mock_environment(self, mock_getenv, dictionary):
        mock_getenv.side_effect = lambda *args: dictionary.get(args[0], args[1] if args.__len__() > 1 else None)

import operator
from datetime import datetime, timedelta
from threading import RLock

from cachetools import TTLCache, cachedmethod

import logging


class AWSHostResolver(object):
    """
    Responsible for resolving AWS host details.
    Configures a threadsafe cache of results from AWS to avoid making too many calls to AWS.
    Instances of this class are thread safe, hence a single instance can be used across many threads.
    """

    def __init__(self, ec2_client, dry_run=False, aws_call_interval_secs=10):
        self.logger = logging.getLogger(__name__)
        self.ec2_client = ec2_client
        self.dry_run = dry_run
        self.aws_call_interval_secs = aws_call_interval_secs
        self.aws_cache_expiry_time = datetime.utcnow()
        self.instances = []
        self.ttl_cache = TTLCache(maxsize=1, ttl=self.aws_call_interval_secs)
        self.cache_lock = RLock()

    @cachedmethod(operator.attrgetter('ttl_cache'), lock=operator.attrgetter('cache_lock'))
    def find_running_hosts_private_ip_by_tag(self, tag_name, tag_value):
        """
        Returns a list of private IP address strings
        for any running hosts with the specified tag.
        """
        if datetime.utcnow() > self.aws_cache_expiry_time:
            self.logger.info(dict(Message="Looking for EC2 hosts with tag '{}' and value '{}'".format(tag_name, tag_value)))

            tag_filter = {
                'Name': 'tag:{}'.format(tag_name),
                'Values': [tag_value]
            }
            running_host_filter = {
                'Name': 'instance-state-name',
                'Values': ['running']
            }
            describe_instances_response = self.ec2_client.describe_instances(
                Filters=[tag_filter, running_host_filter],
                DryRun=self.dry_run
            )

            self.logger.info(dict(Message="Describe Instances Response: {}".format(describe_instances_response)))

            reservations = describe_instances_response['Reservations']
            if len(reservations) > 0:
                aws_instances = []
                for reservation in reservations:
                    instances = reservation['Instances']
                    aws_instances.extend(instances)
                self.instances = aws_instances
            else:
                self.instances = []
            self.aws_cache_expiry_time = datetime.utcnow() + timedelta(seconds=self.aws_call_interval_secs)
            self.logger.debug(dict(Message="Cache expiry time updated, now: {}".format(self.aws_cache_expiry_time)))
        else:
            self.logger.debug(dict(Message="Expiry time not reached, using cached data."))

        return [instance['PrivateIpAddress'] for instance in self.instances]
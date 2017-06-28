import logging

from datetime import datetime, timedelta
from threading import BoundedSemaphore

logger = logging.getLogger('aws_host_resolver')


class AWSHostResolver(object):
    """
    Responsible for resolving AWS host details.
    Maintains a cache of results from AWS to avoid making too many calls to AWS.
    Instances of this class are thread safe, hence a single instance can be used across many threads.
    """

    def __init__(self, ec2_client, dry_run=False, max_results=1000, aws_call_interval_secs=10):
        self.ec2_client = ec2_client
        self.dry_run = dry_run
        self.max_results = max_results
        self.aws_call_interval_secs = aws_call_interval_secs
        self.aws_cache_expiry_time = datetime.utcnow()
        self.instances = []
        self.cache_semaphore = BoundedSemaphore(value=1)

    def find_running_hosts_private_ip_by_tag(self, tag_name, tag_value):
        """
        Returns a list of private IP address strings
        for any running hosts with the specified tag.
        """
        self.cache_semaphore.acquire()
        logger.debug(dict(Message="Locking semaphore acquired."))

        if datetime.utcnow() > self.aws_cache_expiry_time:
            logger.info(dict(Message="Looking for EC2 hosts with tag '{}' and value '{}'".format(tag_name, tag_value)))

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

            logger.info(dict(Message="Describe Instances Response: {}".format(describe_instances_response)))

            if len(describe_instances_response['Reservations']) > 0:
                self.instances = describe_instances_response['Reservations'][0]['Instances']
            else:
                self.instances = []
            self.aws_cache_expiry_time = datetime.utcnow() + timedelta(seconds=self.aws_call_interval_secs)
            logger.debug(dict(Message="Cache expiry time updated, now: {}".format(self.aws_cache_expiry_time)))
        else:
            logger.debug(dict(Message="Expiry time not reached, using cached data."))

        self.cache_semaphore.release()
        logger.debug(dict(Message="Locking semaphore released."))

        return [instance['PrivateIpAddress'] for instance in self.instances]

import logging


class AWSHostResolver(object):

    def __init__(self, ec2_client, dry_run=False, max_results=1000):
        self.ec2_client = ec2_client
        self.dry_run = dry_run
        self.max_results = max_results

    def find_running_hosts_private_ip_by_tag(self, tag_name, tag_value):
        """
        Returns a list of private IP address strings
        for any running hosts with the specified tag.
        """
        logging.debug("Looking for EC2 hosts with tag: {} and value: {}".format(tag_name, tag_value))

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

        logging.debug("Describe Instances Response: {}".format(describe_instances_response))

        if len(describe_instances_response['Reservations']) > 0:
            instances = describe_instances_response['Reservations'][0]['Instances']
        else:
            instances = []

        return [instance['PrivateIpAddress'] for instance in instances]

import unittest

from botocore.session import Session
from botocore.stub import Stubber

from captain.aws_host_resolver import AWSHostResolver

#TODO: Look at using https://github.com/spulec/moto


class TestAWSHostResolver(unittest.TestCase):

    def setUp(self):
        #TODO: Figure out how to set up boto so it doesn't want MFA during tests.
        self.session = Session(profile='service-prototypes-engineer')
        self.ec2_client = self.session.create_client('ec2')
        self.ec2_client_stubber = Stubber(self.ec2_client)
        self.under_test = AWSHostResolver(self.ec2_client)

    def test_it_should_resolve_hosts_from_tags(self):
        # Given
        tag_name = 'role'
        tag_value = 'applicationservers'

        private_ip_addresses = ['172.31.14.146', '172.31.14.147']

        expected_response = {
            'Reservations': [
                {
                    'Instances': [
                        {'InstanceId': 'i-0fb9bc94c497fc22b', 'PrivateIpAddress': private_ip_addresses[0]},
                        {'InstanceId': 'i-0fb9bc94c497fc22c', 'PrivateIpAddress': private_ip_addresses[1]}
                    ]
                }
            ]
        }

        expected_params = {
            'Filters': [
                {
                    'Name': 'tag:role',
                    'Values': [
                        tag_value,
                    ]
                },
                {
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }
            ],
            'DryRun': False
        }

        self.ec2_client_stubber.add_response('describe_instances',
                                             expected_response,
                                             expected_params)
        self.ec2_client_stubber.activate()

        # When
        actual_response = self.under_test.find_running_hosts_by_tag(tag_name, tag_value)

        # Then
        self.assertEqual(private_ip_addresses, actual_response)
import unittest

import boto3
from moto import mock_ec2

from captain.aws_host_resolver import AWSHostResolver


class TestAWSHostResolver(unittest.TestCase):

    def setUp(self):
        self.ec2_resource = boto3.resource('ec2')
        self.ec2_client = self.ec2_resource.meta.client
        self.under_test = AWSHostResolver(self.ec2_client)

    @mock_ec2
    def test_it_should_return_private_ip_addresses_of_tagged_hosts(self):
        # Given
        tag_name = 'role'
        tag_value = 'applicationservers'

        untagged_instances = self.ec2_resource.create_instances(ImageId='some-ami-id', MinCount=2, MaxCount=2)
        tagged_instances = self.ec2_resource.create_instances(ImageId='some-ami-id', MinCount=2, MaxCount=2)

        for instance in tagged_instances:
            instance.create_tags(
                Tags=[
                    {
                        'Key': tag_name,
                        'Value': tag_value
                    }
                ]
            )

        # When
        actual_response = self.under_test.find_running_hosts_private_ip_by_tag(tag_name, tag_value)

        # Then
        self.assertTrue(2, len(actual_response))
        for untagged_instance in untagged_instances:
            self.assertNotIn(untagged_instance.private_ip_address, actual_response)
        for tagged_instance in tagged_instances:
            self.assertIn(tagged_instance.private_ip_address, actual_response)

    @mock_ec2
    def test_it_should_return_an_empty_list_when_no_hosts_are_matched(self):
        # Given
        tag_name = 'role'
        tag_value = 'applicationservers'

        # When
        actual_response = self.under_test.find_running_hosts_private_ip_by_tag(tag_name, tag_value)

        # Then
        self.assertLessEqual([], actual_response)
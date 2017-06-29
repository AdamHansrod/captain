import unittest

import boto3
import time

import logging

import datetime
from mock import MagicMock
from moto import mock_ec2

from captain.aws_host_resolver import AWSHostResolver
from captain.tests import aws_utils

# Useful logging configuration for seeing which thread is doing what.
# Don't forget to set the --nologcapture flag to stop nosetest silencing logging.
logger = logging.getLogger('test_aws_host_resolver')
logging.basicConfig(level=logging.DEBUG, format='%(relativeCreated)6d %(threadName)s %(message)s')


class TestAWSHostResolver(unittest.TestCase):

    @mock_ec2
    def setUp(self):
        aws_utils.setup_dummy_aws_creds()
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

    def test_it_should_only_hit_aws_once_per_configured_time_period(self):
        # Given
        ec2_client_mock = MagicMock()
        self.under_test = AWSHostResolver(ec2_client_mock)

        # When
        ec2_client_mock.describe_instances.return_value = \
            {'Reservations':
                [
                    {'Instances':
                         [{'PrivateIpAddress': '1.1.1.1'}]
                     }
                ]
            }

        for count in range(10):
            self.under_test.find_running_hosts_private_ip_by_tag(None, None)

        # Then
        self.assertEquals(1, ec2_client_mock.describe_instances.call_count)

    def test_it_should_only_hit_aws_once_per_configured_time_period(self):
        # Given
        aws_call_interval_secs = 1
        ec2_client_mock = MagicMock()
        self.under_test = AWSHostResolver(ec2_client_mock, aws_call_interval_secs=aws_call_interval_secs)

        # When
        ec2_client_mock.describe_instances.return_value = \
            {'Reservations':
                [
                    {'Instances':
                         [{'PrivateIpAddress': '1.1.1.1'}]
                     }
                ]
            }

        for count in range(2):
            time.sleep(1)
            self.under_test.find_running_hosts_private_ip_by_tag(None, None)

        # Then
        self.assertEquals(2, ec2_client_mock.describe_instances.call_count)

    def test_cache_configuration_results_in_expected_number_of_method_calls(self):
        # Given
        test_duration_secs = 2
        aws_call_interval_secs = 1
        ec2_client_mock = MagicMock()
        self.under_test = AWSHostResolver(ec2_client_mock, aws_call_interval_secs=aws_call_interval_secs)
        responses = list()

        start_time = datetime.datetime.utcnow()
        end_time = start_time + datetime.timedelta(seconds=test_duration_secs)
        expected_number_of_method_calls = test_duration_secs / aws_call_interval_secs

        # When
        ec2_client_mock.describe_instances.return_value = \
            {'Reservations':
                [
                    {'Instances':
                         [{'PrivateIpAddress': '1.1.1.1'}]
                     }
                ]
            }

        number_of_method_invocations = 0
        while datetime.datetime.utcnow() < end_time:
            response = self.under_test.find_running_hosts_private_ip_by_tag(None, None)
            responses.append(response)
            number_of_method_invocations += 1
        logger.info("Requests complete, made {} requests in {} seconds".format(number_of_method_invocations, test_duration_secs))

        # Then
        self.assertEquals(expected_number_of_method_calls, ec2_client_mock.describe_instances.call_count)

        for response in responses:
            self.assertEquals(['1.1.1.1'], response)


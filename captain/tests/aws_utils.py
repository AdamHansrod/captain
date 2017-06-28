import os


def setup_dummy_aws_creds():
    os.environ['AWS_DEFAULT_REGION'] = "eu-west-1"
    os.environ['AWS_ACCESS_KEY_ID'] = "my pretend AWS access key id - irrelevant as we're mocking AWS with Moto"
    os.environ['AWS_SECRET_ACCESS_KEY'] = "my pretend AWS secret access key id - irrelevant as we're mocking AWS with Moto"
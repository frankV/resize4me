import pytest
import boto3
import json
from moto import mock_s3
from copy import deepcopy
from resize4me import Resize4Me


CONFIG = {
    'source_bucket': 'workman-photo-bucket',
    'destination_buckets': [
        {
            'name': 'workman-photo-bucket',
            'width_size': 300
        },
        {
            'name': 'workman-photo-bucket',
            'width_size': 600
        }
    ]
}


def test_parse_config(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))
    r4m = Resize4Me(config_file)
    assert r4m.parse_config(config_file)


def test_parse_config_without_file(tmpdir):
    with pytest.raises(FileNotFoundError):
        Resize4Me('file_not_found.json')


def test_parse_config_without_source_bucket(tmpdir):
    config = deepcopy(CONFIG)
    config.pop('source_bucket')
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(config))
    with pytest.raises(ValueError):
        r4m = Resize4Me(config_file)
        r4m.parse_config(config_file)


def test_parse_config_without_destination_buckets(tmpdir):
    config = deepcopy(CONFIG)
    config.pop('destination_buckets')
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(config))
    with pytest.raises(ValueError):
        r4m = Resize4Me(config_file)
        r4m.parse_config(config_file)


def test_parse_config_without_destination_buckets_name(tmpdir):
    config = deepcopy(CONFIG)
    config['destination_buckets'][0].pop('name')
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(config))
    with pytest.raises(ValueError):
        r4m = Resize4Me(config_file)
        r4m.parse_config(config_file)


def test_parse_config_without_destination_buckets_width_size(tmpdir):
    config = deepcopy(CONFIG)
    config['destination_buckets'][0].pop('width_size')
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(config))
    with pytest.raises(ValueError):
        r4m = Resize4Me(config_file)
        r4m.parse_config(config_file)


@mock_s3
def test_verify_buckets(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))

    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='resize4me')
    conn.create_bucket(Bucket='resize4me-300px')
    conn.create_bucket(Bucket='resize4me-600px')

    r4m = Resize4Me(config_file)
    r4m.verify_buckets()


@mock_s3
def test_verify_buckets_non_valid_bucket(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))

    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='bucket_outside_configuration')

    with pytest.raises(Exception):
        r4m = Resize4Me(config_file)
        r4m.verify_buckets()


@pytest.mark.parametrize('input, output', [
    ('file.png', '.png'),
    ('file.jpg', '.jpg'),
    ('file.jpeg', '.jpeg'),
])
def test_check_valid_extension(tmpdir, input, output):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))
    r4m = Resize4Me(config_file)
    extension = r4m.check_extension(input)
    assert extension == output


def test_check_invalid_extension(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))
    with pytest.raises(ValueError):
        r4m = Resize4Me(config_file)
        r4m.check_extension('some_file.exe')


@mock_s3
def test_upload(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))

    conn = boto3.resource('s3', region_name='us-east-1')
    conn.create_bucket(Bucket='resize4me')

    r4m = Resize4Me(config_file)
    r4m.upload('resize4me', 'key', 'body')

    body = conn.Object(
        'resize4me',
        'key'
    ).get()['Body'].read().decode('utf-8')

    assert body == 'body'


def test_response(tmpdir):
    config_file = tmpdir.join('resize4me_settings.json')
    config_file.write(json.dumps(CONFIG))
    r4m = Resize4Me(config_file)

    response = {
        'resize4me': 'https://s3.amazonaws.com/resize4me/file.jpg',
        'resized-300px': 'https://s3.amazonaws.com/resize4me-300px/file.jpg',
        'resized-600px': 'https://s3.amazonaws.com/resize4me-600px/file.jpg',

    }
    actual_response = r4m.response('file.jpg')
    assert response == actual_response

import boto3
import PIL
import json
from io import BytesIO
from os import path
from urllib.parse import quote_plus, unquote_plus
from PIL import Image
from botocore.client import ClientError


class Resize4Me():
    """
    Resizes and uplodads images do an S3 bucket.
    """

    def __init__(self):
        self.s3 = boto3.resource('s3')
        self.source_bucket = None
        self.destination_buckets = None
        self.config = self.parse_config()
        self.verify_buckets()

    def parse_config(self):
        """
        Parses and verifies if the configuration file is correct,
        which should be in the project root directory, named as
        resize4me_settings.json.

        Returns:
        <dict> config - the configuration file in a dictionary.
        """

        with open('resize4me_settings.json', 'r') as file:
            config = json.loads(file.read())

        self.source_bucket = config.get('source_bucket')
        self.destination_buckets = config.get('destination_buckets')

        if not self.source_bucket:
            raise Exception('A source bucket must be configured')

        if not self.destination_buckets or len(self.destination_buckets) == 0:
            raise Exception('At least one destination bucket must be configured')

        for bucket in self.destination_buckets:
            if not bucket.get('name'):
                raise Exception('A destination bucket must have a name')
            if not bucket.get('size'):
                raise Exception('A destination bucket must have a size')

        return config

    def verify_buckets(self):
        """
        Verifies if the buckets specified in the configuration file
        are accessible.
        """

        buckets = [bucket.get('name') for bucket in self.destination_buckets]
        buckets.append(self.source_bucket)

        try:
            for bucket in buckets:
                self.s3.meta.client.head_bucket(Bucket=bucket)
        except ClientError as e:
            raise Exception('Bucket {}: {}'.format(bucket, e))

    def check_extension(self, key):
        """
        Verifies if the file extension is valid.
        Valid formats are JPG and PNG.

        Args:
        <str> key - a filename (usually an S3 object key).

        Returns:
        <str> extension - the file/key extesion, including the dot.
        """

        extension = path.splitext(key)[1].lower()

        if extension.lower() in [
            '.jpg',
            '.jpeg',
            '.png',
        ]:
            return extension
        else:
            raise Exception('File format not supported')

    def resize_image(self, body, extension, size):
        """
        Resizes proportionally an image using `size` as the base width.

        Args:
        <bytesIO> body - the image content in a buffer.
        <str> extension - the image extension.
        <int> size - base width used to the resize process.

        Returns:
        <bytesIO> buffer - returns the image content resized.
        """

        img = Image.open(BytesIO(body))
        wpercent = (size / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((size, hsize), PIL.Image.ANTIALIAS)

        buffer = BytesIO()

        if extension in ['.jpeg', '.jpg']:
            format = 'JPEG'
        if extension in ['.png']:
            format = 'PNG'

        img.save(buffer, format)
        buffer.seek(0)

        return buffer

    def upload(self, bucket_name, key, body):
        """
        Uploads a file to an S3 bucket with `public-read` ACL.

        Args:
        <str> bucket_name - S3 bucket name.
        <str> key - S3 object key.
        <binary> body - the content of the file to be uplodaded.
        """

        obj = self.s3.Object(
            bucket_name=bucket_name,
            key=key,
        )
        obj.put(ACL='public-read', Body=body)

        print('File saved at {}/{}'.format(
            bucket_name,
            key,
        ))

    def response(self, key):
        """
        Gerenates a dictionary response with all objects generated.

        Args:
        <str> key - S3 key from the file uploaded.

        Returns:
        <dict> response - dictonary with all generated files.
        """

        aws_domain = 'https://s3.amazonaws.com'
        response = {
            self.source_bucket: '{}/{}/{}'.format(
                aws_domain,
                self.source_bucket,
                quote_plus(key),
            )
        }

        for bucket in self.destination_buckets:
            dict_key = 'resized-{}px'.format(bucket.get('size'))
            response[dict_key] = 'https://s3.amazonaws.com/{}/{}'.format(
                bucket.get('name'),
                quote_plus(key),
            )

        return response


def lambda_handler(event, context):
    """
    Given a configuration file with source_bucket and destination_buckets,
    will resize any valid file uploaded to the source_bucket and save
    into the destination bucket.
    """

    r4me = Resize4Me()

    for object in event.get('Records'):
        object_key = unquote_plus(object['s3']['object']['key'])
        object_extension = r4me.check_extension(object_key)

        # Source file
        obj = r4me.s3.Object(
            bucket_name=r4me.source_bucket,
            key=object_key,
        )
        obj_body = obj.get()['Body'].read()

        # Resized files
        for bucket in r4me.destination_buckets:
            bucket_name = bucket.get('name')
            bucket_size = bucket.get('size')

            resized_image = r4me.resize_image(
                obj_body,
                object_extension,
                bucket_size
            )
            r4me.upload(bucket_name, object_key, resized_image)

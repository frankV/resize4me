import boto3, PIL, json
from io import BytesIO
from os import path
from urllib.parse import quote_plus, unquote_plus
from PIL import Image
from botocore.client import ClientError
from itertools import product


class Resize4Me():
    """
    Resizes and uplodads images do an S3 bucket.
    """

    def __init__(self, config_file='resize4me_settings.json'):
        self.s3 = boto3.resource('s3')
        self.source_bucket = None
        self.destination_buckets = None
        self.config = self.parse_config(config_file)

    def parse_config(self, config_file):
        """
        Parses and verifies if the configuration file is correct,
        which should be in the project root directory, named as
        resize4me_settings.json.

        Returns:
        <dict> config - the configuration file in a dictionary.
        """

        with open(config_file, 'r') as file:
            config = json.loads(file.read())

        self.source_bucket = config.get('bucket')
        self.destination_buckets = config.get('bucket')

        if not self.source_bucket:
            raise ValueError('A source bucket must be configured')

        return config

    def metadata(self, key):
        client = boto3.client('s3')
        return client.head_object(Bucket=self.source_bucket, Key=key)['Metadata']

    def verify_buckets(self):
        """
        Verifies if the buckets specified in the configuration file
        are accessible.
        """

        try:
            for bucket in [self.source_bucket, self.destination_buckets]:
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
            raise ValueError('File format not supported')

    def resize_image(self, body, extension, size, rfilter):
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
        img = img.resize((size, hsize), rfilter)

        buffer = BytesIO()

        if extension in ['.jpeg', '.jpg']:
            format = 'JPEG'
        if extension in ['.png']:
            format = 'PNG'

        img.save(buffer, format)
        buffer.seek(0)

        return buffer

    def rename(self, key, size, rfilter):
        FILTERS = {
            0: 'NEAREST',
            1: 'LANCZOS',
            2: 'BILINEAR',
            3: 'BICUBIC',
            4: 'BOX',
            5: 'HAMMING'
        }
        filename, ext = path.splitext(path.basename(key))
        return 'resized/{0}-{1}__{2}{3}'.format(filename, size, FILTERS[rfilter], ext)

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
        obj.put(
            ACL='public-read',
            Body=body,
            Metadata={'image-processed': 'true'}
        )

        print('File saved at {}/{}'.format(bucket_name, key))


def lambda_handler(event, context):
    """
    Given a configuration file with source_bucket and destination_buckets,
    will resize any valid file uploaded to the source_bucket and save
    into the destination bucket.
    """

    r4me = Resize4Me()
    r4me.verify_buckets()

    for object in event.get('Records'):
        object_key = unquote_plus(object['s3']['object']['key'])
        object_extension = r4me.check_extension(object_key)

        # Source file
        obj = r4me.s3.Object(
            bucket_name=r4me.source_bucket,
            key=object_key,
        )
        obj_body = obj.get()['Body'].read()

        try:
            meta = r4me.metadata(object_key)
            # skip if image is already processed
            if 'image-processed' in meta and meta['image-processed'] == 'true':
                raise Exception('Already processed image')

            sizes = [300, 600, 900]
            rfilters = [
                PIL.Image.NEAREST,
                PIL.Image.LANCZOS,
                PIL.Image.BILINEAR,
                PIL.Image.BICUBIC,
                PIL.Image.BOX,
                PIL.Image.HAMMING
            ]

            for size, rfilter in list(product(sizes, rfilters)):

                print("RESIZING:::", size, rfilter, object_key)

                resized_image = r4me.resize_image(
                    obj_body,
                    object_extension,
                    size,
                    rfilter
                )

                print("UPLOADING:::", r4me.rename(object_key, size, rfilter))

                r4me.upload(
                    r4me.source_bucket, r4me.rename(object_key, size, rfilter), resized_image)

            return

        except Exception as e:
            print(e)

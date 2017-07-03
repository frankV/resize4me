# Resize4Me
Upload an image to an S3 bucket and see them magically being resized in other buckets!  

A Lambda function will resize images uploaded to your `source_bucket` into any `destination_buckets`.  

A Flask API will also be deployed if, you want an endpoint to upload the images. To use it, just make a `POST` with a `file` form-data parameter.

## Configuration
Clone this repository, configure your AWS keys and create all buckets used.

Specify your buckets in `resize4me_settings.json`:
```
{
    // Bucket that will receive the files to be resized
    "source_bucket": "resize4me",

    // Buckets to receive the resized images,
    // containing the bucket name and the base width for resizing.
    "destination_buckets": [
        {
            "name": "resize4me-300px",
            "size": 300
        }, 
        {
            "name": "resize4me-600px",
            "size": 600
        }
    ]
}
```

Configure your deployment in `zappa_settigs.json`:
```
{
    "production": {
        // Event that generate the images, make sure to specify
        // your source bucket here: arn:aws:s3:::<your-source-bucket>
        "events": [{
            "function": "resize4me.lambda_handler",
            "event_source": {
                "arn": "arn:aws:s3:::resize4me",
                "events": [
                    "s3:ObjectCreated:*"
                ]
            }
        }],
        "profile_name": "default",
        "aws_region": "us-east-1",
        "s3_bucket": "zappa-resize4me",
        "timeout_seconds": 30,

        // If you don't want the Flask API, please remove the line above
        "app_function": "app.app",
        // And add this one
        "apigateway_enabled": false
    }
}
```

## Installation and Usage

```
$ zappa deploy production
...
Your Zappa deployment is live!: https://<address>.execute-api.us-east-1.amazonaws.com/production

$ curl -X POST https://<address>.execute-api.us-east-1.amazonaws.com/production \
  -F file=@image.png
...

{
  "resize4me": "https://s3.amazonaws.com/resize4me/image.png",
  "resized-300px": "https://s3.amazonaws.com/resize4me-300px/image.png",
  "resized-600px": "https://s3.amazonaws.com/resize4me-600px/image.png"
}
```

## Problems, questions, improvements?
Open an issue and let's discuss it :D

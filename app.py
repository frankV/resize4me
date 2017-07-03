from resize4me import Resize4Me
from flask import Flask, request, jsonify
app = Flask(__name__)


@app.route('/', methods=['POST'])
def upload_file():
    """
    Uplodas a file to a S3 bucket and returns a list of dicts
    with the generated resized files.
    """

    if 'file' not in request.files:
        return 'No file uploaded'

    file = request.files['file']

    resize4me = Resize4Me()
    resize4me.check_extension(file.filename)

    resize4me.upload(
        resize4me.source_bucket,
        file.filename,
        file.stream.read()
    )

    response = resize4me.response(file.filename)

    return jsonify(response)


if __name__ == '__main__':
    app.run()

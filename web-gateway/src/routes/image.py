import urllib.request
import urllib.error

from flask import Blueprint, request, jsonify

image_bp = Blueprint("image", __name__)

IMAGE_WORKER = "http://image-worker:5000"


@image_bp.route("/api/images/upload", methods=["POST"])
def upload_image():

    if "image" not in request.files:
        return jsonify({"error": "image is required"}), 400

    image = request.files["image"]

    if image.filename == "":
        return jsonify({"error": "no filename"}), 400

    data = image.read()

    boundary = "----AIS3ImageUploadBoundary"

    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; '
        f'filename="{image.filename}"\r\n'
        f"Content-Type: {image.content_type or 'application/octet-stream'}\r\n"
        f"\r\n"
    ).encode()

    body += data

    body += (
        f"\r\n--{boundary}--\r\n"
    ).encode()

    req = urllib.request.Request(
        f"{IMAGE_WORKER}/upload",
        data=body,
        method="POST",
        headers={
            "Content-Type":
                f"multipart/form-data; boundary={boundary}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode()

        return result, 200, {
            "Content-Type": "application/json"
        }

    except urllib.error.HTTPError as e:
        return jsonify({
            "error": "image worker rejected upload",
            "detail": e.read().decode()
        }), e.code

    except Exception as e:
        return jsonify({
            "error": "image worker unavailable",
            "detail": str(e)
        }), 502

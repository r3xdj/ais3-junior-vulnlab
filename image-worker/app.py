from flask import Flask, request, jsonify, send_from_directory
import os
import uuid
import subprocess

app = Flask(__name__)

UPLOAD_DIR = "/app/uploads"
OUTPUT_DIR = "/app/output"

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "image is required"}), 400

    image = request.files["image"]

    if image.filename == "":
        return jsonify({"error": "no filename"}), 400

    file_id = uuid.uuid4().hex

    input_path = os.path.join(
        UPLOAD_DIR,
        file_id + ".img"
    )

    output_name = file_id + ".png"

    output_path = os.path.join(
        OUTPUT_DIR,
        output_name
    )

    image.save(input_path)

    try:
        subprocess.run(
            [
                "convert",
                input_path,
                "-thumbnail",
                "300x300",
                output_path
            ],
            check=True,
            capture_output=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        return jsonify({
            "error": "image processing failed",
            "detail": e.stderr
        }), 400

    return jsonify({
        "status": "success",
        "file": output_name
    })


@app.route("/output/<filename>")
def output(filename):
    return send_from_directory(
        OUTPUT_DIR,
        filename
    )


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000
    )

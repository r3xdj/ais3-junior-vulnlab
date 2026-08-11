from flask import Blueprint, request, jsonify
from decorators import require_admin
import urllib.parse
from io import BytesIO
import pycurl

webhook_bp = Blueprint('webhook', __name__, url_prefix='/api/admin')


def _fetch_url(target_url):
    parsed = urllib.parse.urlparse(target_url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError('Invalid URL format')

    if parsed.hostname in ('127.0.0.1', 'localhost'):
        raise PermissionError('Blocked: cannot connect to loopback address')

    buffer = BytesIO()
    c = pycurl.Curl()
    try:
        c.setopt(pycurl.CAINFO,"/etc/ssl/certs/ca-certificates.crt")
        c.setopt(pycurl.URL, target_url)
        c.setopt(pycurl.WRITEDATA, buffer)
        c.setopt(pycurl.TIMEOUT, 5)
        c.perform()
        status = c.getinfo(pycurl.RESPONSE_CODE)
        body = buffer.getvalue().decode('utf-8', errors='replace')
        return status, body
    except pycurl.error as e:
        args = e.args
        if len(args) == 2:
            errno, errstr = args
        else:
            errno = None
            errstr = args[0] if args else ''
        partial = buffer.getvalue()
        if errno == 28 and partial:
            return 'partial_response_on_timeout', partial.decode('utf-8', errors='replace')
        raise RuntimeError(errstr)
    finally:
        c.close()


@webhook_bp.route('/webhook-test', methods=['POST'])
@require_admin
def webhook_test():
    payload = request.get_json(silent=True) or {}
    target_url = payload.get('url') or request.form.get('url', '')
    if not target_url:
        return jsonify({"error": "Missing url field"}), 400

    try:
        status, body = _fetch_url(target_url)
        return jsonify({"status": status, "body": body})
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502


@webhook_bp.route('/fetch-report', methods=['GET', 'POST'])
@require_admin
def fetch_report():
    payload = request.get_json(silent=True) or {}
    target_url = request.args.get('url') or payload.get('url') or request.form.get('url', '')
    if not target_url:
        return jsonify({"error": "Missing url field"}), 400

    try:
        status, body = _fetch_url(target_url)
        return jsonify({"status": status, "body": body})
    except PermissionError as exc:
        return jsonify({"error": str(exc)}), 403
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except RuntimeError as exc:
        return jsonify({"error": str(exc)}), 502
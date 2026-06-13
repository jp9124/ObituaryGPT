import base64
import hashlib
import json
import mimetypes
import os
import time
import uuid
from datetime import datetime, timezone
from email import policy
from email.parser import BytesParser
from urllib import request
from urllib.error import HTTPError

import boto3


dynamodb = boto3.resource("dynamodb")
polly = boto3.client("polly")
ssm = boto3.client("ssm")

table = dynamodb.Table(os.environ["OBITUARIES_TABLE"])

SSM_PARAMETER_PATH = os.environ.get("SSM_PARAMETER_PATH", "/last-show/")
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-5.5")
POLLY_VOICE_ID = os.environ.get("POLLY_VOICE_ID", "Joanna")
CLOUDINARY_FOLDER = os.environ.get("CLOUDINARY_FOLDER", "last-show")


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "content-type",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body),
    }


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return response(204, {})

    try:
        fields, files = parse_request(event)
        name = require_field(fields, "name")
        born = require_field(fields, "born")
        died = require_field(fields, "died")
        picture = files.get("picture")

        if not picture:
            return response(400, {"message": "Picture is required"})

        secrets = get_secrets()
        item_id = str(uuid.uuid4())
        born_year = born[:4]
        died_year = died[:4]

        obituary = generate_obituary(secrets["openai_api_key"], name, born_year, died_year)
        audio_bytes = synthesize_obituary(obituary)

        image_upload = upload_to_cloudinary(
            secrets=secrets,
            resource_type="image",
            file_bytes=picture["content"],
            filename=picture["filename"] or f"{item_id}.jpg",
            public_id=f"{item_id}-portrait",
        )
        audio_upload = upload_to_cloudinary(
            secrets=secrets,
            resource_type="video",
            file_bytes=audio_bytes,
            filename=f"{item_id}.mp3",
            public_id=f"{item_id}-speech",
            content_type="audio/mpeg",
        )

        item = {
            "id": item_id,
            "name": name,
            "born": born,
            "died": died,
            "picture": add_zorro_effect(image_upload["secure_url"]),
            "audio": audio_upload["secure_url"],
            "obituary": obituary,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        table.put_item(Item=item)
        return response(201, item)
    except ValueError as error:
        return response(400, {"message": str(error)})
    except Exception as error:
        print(f"Failed to create obituary: {error}")
        return response(500, {"message": "Could not create obituary"})


def parse_request(event):
    headers = {key.lower(): value for key, value in event.get("headers", {}).items()}
    content_type = headers.get("content-type", "")
    raw_body = event.get("body") or ""

    if event.get("isBase64Encoded"):
        body = base64.b64decode(raw_body)
    else:
        body = raw_body.encode("utf-8")

    if content_type.startswith("application/json"):
        data = json.loads(body.decode("utf-8"))
        return data, {}

    if not content_type.startswith("multipart/form-data"):
        raise ValueError("Request must be multipart/form-data")

    message = BytesParser(policy=policy.default).parsebytes(
        b"Content-Type: "
        + content_type.encode("utf-8")
        + b"\r\nMIME-Version: 1.0\r\n\r\n"
        + body
    )

    fields = {}
    files = {}

    for part in message.iter_parts():
        disposition = part.get("Content-Disposition", "")
        if "form-data" not in disposition:
            continue

        params = dict(part.get_params(header="content-disposition"))
        field_name = params.get("name")
        filename = params.get("filename")

        if not field_name:
            continue

        payload = part.get_payload(decode=True) or b""

        if filename:
            files[field_name] = {
                "filename": filename,
                "content_type": part.get_content_type(),
                "content": payload,
            }
        else:
            fields[field_name] = payload.decode("utf-8").strip()

    return fields, files


def require_field(fields, name):
    value = fields.get(name)
    if not value:
        raise ValueError(f"{name} is required")
    return value


def get_secrets():
    parameters = {}
    next_token = None

    while True:
        kwargs = {
            "Path": SSM_PARAMETER_PATH,
            "Recursive": True,
            "WithDecryption": True,
        }
        if next_token:
            kwargs["NextToken"] = next_token

        result = ssm.get_parameters_by_path(**kwargs)
        for parameter in result.get("Parameters", []):
            key = parameter["Name"].rstrip("/").split("/")[-1].lower()
            parameters[key] = parameter["Value"]

        next_token = result.get("NextToken")
        if not next_token:
            break

    aliases = {
        "openai_api_key": ["openai_api_key", "openai-key", "openai"],
        "cloudinary_cloud_name": ["cloudinary_cloud_name", "cloud_name"],
        "cloudinary_api_key": ["cloudinary_api_key", "api_key"],
        "cloudinary_api_secret": ["cloudinary_api_secret", "api_secret"],
    }

    secrets = {}
    for target, possible_names in aliases.items():
        for possible_name in possible_names:
            if possible_name in parameters:
                secrets[target] = parameters[possible_name]
                break

    missing = [key for key in aliases if key not in secrets]
    if missing:
        raise ValueError(f"Missing SSM parameters: {', '.join(missing)}")

    return secrets


def generate_obituary(api_key, name, born_year, died_year):
    prompt = (
        "Write a warm, respectful obituary about a fictional character named "
        f"{name} who was born in {born_year} and died in {died_year}. "
        "Keep it under 180 words."
    )
    payload = {
        "model": OPENAI_MODEL,
        "input": prompt,
        "max_output_tokens": 600,
    }

    result = post_json(
        "https://api.openai.com/v1/responses",
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    if result.get("output_text"):
        return result["output_text"].strip()

    for output in result.get("output", []):
        for content in output.get("content", []):
            if content.get("type") in ["output_text", "text"] and content.get("text"):
                return content["text"].strip()

    raise RuntimeError("OpenAI response did not include text")


def synthesize_obituary(obituary):
    result = polly.synthesize_speech(
        Text=obituary,
        OutputFormat="mp3",
        VoiceId=POLLY_VOICE_ID,
    )
    return result["AudioStream"].read()


def upload_to_cloudinary(
    secrets,
    resource_type,
    file_bytes,
    filename,
    public_id,
    content_type=None,
):
    timestamp = str(int(time.time()))
    params = {
        "folder": CLOUDINARY_FOLDER,
        "public_id": public_id,
        "timestamp": timestamp,
    }
    signature = sign_cloudinary_params(params, secrets["cloudinary_api_secret"])
    fields = {
        **params,
        "api_key": secrets["cloudinary_api_key"],
        "signature": signature,
    }
    body, boundary = build_multipart_body(
        fields,
        "file",
        filename,
        file_bytes,
        content_type or guess_content_type(filename),
    )
    url = (
        f"https://api.cloudinary.com/v1_1/{secrets['cloudinary_cloud_name']}/"
        f"{resource_type}/upload"
    )

    return post_multipart(url, body, boundary)


def sign_cloudinary_params(params, api_secret):
    signature_base = "&".join(f"{key}={params[key]}" for key in sorted(params))
    return hashlib.sha1(f"{signature_base}{api_secret}".encode("utf-8")).hexdigest()


def build_multipart_body(fields, file_field, filename, file_bytes, content_type):
    boundary = f"----last-show-{uuid.uuid4().hex}"
    chunks = []

    for key, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"),
                str(value).encode("utf-8"),
                b"\r\n",
            ]
        )

    chunks.extend(
        [
            f"--{boundary}\r\n".encode("utf-8"),
            (
                f'Content-Disposition: form-data; name="{file_field}"; '
                f'filename="{filename}"\r\n'
            ).encode("utf-8"),
            f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
            file_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode("utf-8"),
        ]
    )

    return b"".join(chunks), boundary


def post_json(url, payload, headers):
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(url, data=body, headers=headers, method="POST")
    return read_json_response(req)


def post_multipart(url, body, boundary):
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    return read_json_response(req)


def read_json_response(req):
    try:
        with request.urlopen(req, timeout=25) as res:
            return json.loads(res.read().decode("utf-8"))
    except HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP request failed with {error.code}: {details}") from error


def guess_content_type(filename):
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def add_zorro_effect(url):
    return url.replace("/image/upload/", "/image/upload/e_art:zorro/", 1)

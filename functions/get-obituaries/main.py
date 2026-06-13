import json
import os
from decimal import Decimal

import boto3


dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ["OBITUARIES_TABLE"])


def response(status_code, body):
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, default=encode_dynamodb),
    }


def encode_dynamodb(value):
    if isinstance(value, Decimal):
        if value % 1 == 0:
            return int(value)
        return float(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def lambda_handler(event, context):
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return response(204, {})

    try:
        items = []
        scan_kwargs = {}

        while True:
            result = table.scan(**scan_kwargs)
            items.extend(result.get("Items", []))

            last_key = result.get("LastEvaluatedKey")
            if not last_key:
                break

            scan_kwargs["ExclusiveStartKey"] = last_key

        items.sort(key=lambda item: item.get("created_at", ""), reverse=True)
        return response(200, {"obituaries": items})
    except Exception as error:
        print(f"Failed to load obituaries: {error}")
        return response(500, {"message": "Could not load obituaries"})

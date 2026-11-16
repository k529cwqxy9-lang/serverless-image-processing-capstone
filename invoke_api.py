"""Send a signed request to the capstone's IAM-authorized HTTP API."""

import argparse
import json
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='ResizeApiUrl from CloudFormation Outputs')
    parser.add_argument('key', help='S3 object key, such as originals/demo.jpg')
    parser.add_argument('--region', default='us-east-1')
    args = parser.parse_args()

    endpoint = urlparse(args.url)
    if (endpoint.scheme != 'https' or not endpoint.hostname
            or not endpoint.hostname.endswith(f'.execute-api.{args.region}.amazonaws.com')
            or endpoint.path != '/resize'):
        parser.error('Use the HTTPS execute-api /resize URL for the selected Region.')

    credentials = boto3.Session().get_credentials()
    if credentials is None:
        parser.error('No AWS credentials were found. Use AWS CloudShell or sign in locally.')

    payload = json.dumps({'key': args.key}).encode('utf-8')
    signed = AWSRequest(method='POST', url=args.url, data=payload,
                        headers={'Content-Type': 'application/json'})
    SigV4Auth(credentials.get_frozen_credentials(), 'execute-api', args.region).add_auth(signed)
    request = Request(args.url, data=payload, method='POST', headers=dict(signed.headers))
    try:
        with urlopen(request, timeout=20) as response:
            print(response.read().decode('utf-8'))
    except HTTPError as exc:
        raise SystemExit(f'HTTP {exc.code}: {exc.read().decode("utf-8")}') from exc


if __name__ == '__main__':
    main()

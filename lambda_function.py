"""Resize one image requested by Step Functions or by an S3 upload."""

import logging
import os
from io import BytesIO
from urllib.parse import unquote_plus

import boto3
from botocore.exceptions import ClientError
from PIL import Image, ImageOps, UnidentifiedImageError

s3 = boto3.client('s3')
log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
MAX_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 20_000_000


def resize_image(key, channel):
    source = os.environ['ORIGINALS_BUCKET']
    destination = os.environ['THUMBNAILS_BUCKET']
    if not isinstance(key, str) or not key.startswith('originals/') or key.endswith('/'):
        return {'success': False, 'reason': 'Use an object key under originals/.'}

    try:
        response = s3.get_object(Bucket=source, Key=key)
        with response['Body'] as body:
            if response['ContentLength'] > MAX_BYTES:
                return {'success': False, 'reason': 'Image is larger than 10 MiB.'}
            data = body.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            return {'success': False, 'reason': 'Image is larger than 10 MiB.'}
    except ClientError as exc:
        if exc.response['Error']['Code'] in ('NoSuchKey', '404'):
            return {'success': False, 'reason': 'Original image was not found.'}
        raise

    try:
        with Image.open(BytesIO(data), formats=['JPEG', 'PNG']) as original:
            image = ImageOps.exif_transpose(original).convert('RGBA')
            image.thumbnail((256, 256), Image.Resampling.LANCZOS)
            output = BytesIO()
            image.save(output, format='PNG')
            width, height = image.size
    except (UnidentifiedImageError, Image.DecompressionBombError, OSError):
        return {'success': False, 'reason': 'The object is not a supported, readable image.'}

    output_key = f'{channel}/{key.removeprefix("originals/")}.png'
    s3.put_object(Bucket=destination, Key=output_key, Body=output.getvalue(), ContentType='image/png')
    log.info('Wrote %s to %s (%s x %s)', output_key, destination, width, height)
    return {'success': True, 'bucket': destination, 'key': output_key, 'width': width, 'height': height}


def lambda_handler(event, context):
    if 'Records' not in event:
        return resize_image(event.get('key'), 'workflow')

    results = []
    for record in event['Records']:
        event_bucket = record['s3']['bucket']['name']
        if event_bucket != os.environ['ORIGINALS_BUCKET']:
            continue
        key = unquote_plus(record['s3']['object']['key'])
        result = resize_image(key, 'automatic')
        if not result['success']:
            log.warning('Skipped %s: %s', key, result['reason'])
        results.append(result)
    return {'results': results}

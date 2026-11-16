# Serverless Image Processing Capstone

The Lambda reads JPEG and PNG images from a private S3 bucket and writes PNG thumbnails to a second bucket. It preserves the aspect ratio and fits the thumbnail within 256 × 256 pixels.

- **Upload:** S3 upload → Lambda → thumbnail under `automatic/`.
- **API request:** API Gateway → Step Functions → Lambda → thumbnail under `workflow/`. The Choice state routes the run to success or failure.

## Run the demo

1. In the originals bucket, upload a JPEG as `originals/demo.jpg`. Open the thumbnails bucket and look for `automatic/demo.jpg.png`.
2. Open AWS CloudShell in the same Region as the stack. Set `RESIZE_API_URL` to the `ResizeApiUrl` value from the CloudFormation stack outputs. Run the following using an AWS identity with permission to invoke the API. Change the signing Region if needed.

   ```bash
   export RESIZE_API_URL='YOUR_RESIZE_API_URL'

   python3 - <<'PY'
   import os
   from urllib.request import Request, urlopen
   import boto3
   from botocore.auth import SigV4Auth
   from botocore.awsrequest import AWSRequest

   url = os.environ["RESIZE_API_URL"]
   body = b'{"key":"originals/demo.jpg"}'
   credentials = boto3.Session().get_credentials().get_frozen_credentials()
   request = AWSRequest(method="POST", url=url, data=body,
                        headers={"Content-Type": "application/json"})
   SigV4Auth(credentials, "execute-api", "us-east-1").add_auth(request)
   with urlopen(Request(url, data=body, headers=dict(request.headers)),
                timeout=20) as response:
       print(response.read().decode())
   PY
   ```

3. Open the returned execution in Step Functions. The success path ends at `ThumbnailCreated` and writes `workflow/demo.jpg.png`. Repeat the request with `originals/missing.jpg` to see the `ResizeFailed` path.

## Deployment settings

The Lambda uses Python 3.12, a Linux x86-64 Pillow layer, and the `lambda_function.lambda_handler` handler. Set its `ORIGINALS_BUCKET` and `THUMBNAILS_BUCKET` environment variables to the two bucket names. Configure the originals bucket to invoke the Lambda on object creation under `originals/`.

In the state machine definition, substitute the Lambda ARN for `${ResizeFunctionArn}`. Give Step Functions permission to invoke that Lambda. Configure API Gateway’s IAM-authorized `POST /resize` route to start the state machine, passing the request body as execution input.

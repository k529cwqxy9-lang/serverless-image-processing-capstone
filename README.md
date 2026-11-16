# Serverless Image Processing Capstone

This project makes PNG thumbnails from JPEG and PNG images in S3. The Lambda uses Pillow to fit the image within 256 × 256 pixels without changing its aspect ratio.

- **Automatic:** Upload an image under `originals/` in the source bucket. S3 invokes the Lambda, which saves the thumbnail under `automatic/` in the output bucket.
- **API:** Send an IAM-signed `POST /resize` request with the source object key. API Gateway starts Step Functions, which invokes the same Lambda. A Choice state sends the execution to success or failure. Successful API runs save a thumbnail under `workflow/`.

```text
S3 upload ────────────────→ Lambda → S3 thumbnails
API Gateway → Step Functions ↗
```

## Deploy

You need AWS permissions for CloudFormation, IAM, S3, Lambda, Step Functions, and API Gateway, plus Python and PowerShell to build the packages. Use a same-Region private S3 bucket for the deployment files. Build the Pillow layer for Python 3.12 and Linux x86-64, then package the Lambda handler separately.

```powershell
python -m pip install --target layer/python --platform manylinux2014_x86_64 --implementation cp --python-version 3.12 --abi cp312 --only-binary=:all: Pillow==12.2.0
Compress-Archive -Path layer/python -DestinationPath pillow-layer.zip
Compress-Archive -Path lambda_function.py -DestinationPath resize-code.zip
```

Upload those two ZIPs and `state-machine.asl.json` to the root of the deployment bucket. In CloudFormation, create a stack with `template.json`, set the `AssetsBucket` parameter, and acknowledge IAM resource creation. The stack outputs show the originals bucket, thumbnails bucket, workflow ARN, and API URL.

## Try it

1. Upload a JPEG as `originals/demo.jpg` in the originals bucket. Look for `automatic/demo.jpg.png` in the thumbnails bucket.
2. From an authenticated AWS environment with Boto3 and permission to invoke the API, run `python3 invoke_api.py YOUR_API_URL originals/demo.jpg`. Use the `ResizeApiUrl` stack output. If you deployed outside N. Virginia, add `--region YOUR_REGION`.
3. Open the returned execution in Step Functions and confirm it reached `ThumbnailCreated`. Look for `workflow/demo.jpg.png` in the thumbnails bucket.
4. Repeat with `originals/missing.jpg` to see the `ResizeFailed` branch.

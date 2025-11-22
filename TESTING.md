# Testing Guide

## Simulating Production Locally

To ensure your changes work in the production environment (which uses S3 and distributed services), you can simulate this setup locally.

### Prerequisites
1.  **AWS Credentials**: Ensure your `.env` file has valid AWS credentials:
    ```bash
    AWS_ACCESS_KEY_ID=your_key
    AWS_SECRET_ACCESS_KEY=your_secret
    S3_BUCKET_NAME=your_bucket
    S3_REGION=us-east-1
    ```

### Running in "Production Mode"
You need to start your services with `STORAGE_TYPE=s3`. This forces the application to use the S3 storage logic instead of the local filesystem.

#### 1. Start the Backend API
```bash
STORAGE_TYPE=s3 backend/venv/bin/python backend/main.py
```

#### 2. Start the Worker
In a separate terminal:
```bash
STORAGE_TYPE=s3 backend/venv/bin/rq worker analysis --path backend
```

#### 3. Run Verification
You can now use the verification script to test the upload flow. It will upload a file, which the API will stage to S3, and the Worker will download from S3.

```bash
python backend/verify_upload_fix_v2.py
```

### Verification Scripts
-   `backend/verify_upload_fix_v2.py`: Simulates a full upload flow (Upload -> Job Processing -> Wardrobe Update).
-   `backend/verify_cleanup.py`: Verifies that staged files are correctly deleted from S3 after processing.

### Switching Back to Development
Simply restart your services without the `STORAGE_TYPE=s3` flag (or set it to `local`) to return to using local filesystem storage.

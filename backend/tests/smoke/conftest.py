"""
Smoke test fixtures and mocks.
These tests run fast (<30s) with mocked external services.
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

# Set test environment variables before importing app
os.environ.setdefault('STORAGE_TYPE', 'local')
os.environ.setdefault('OPENAI_API_KEY', 'test-key-for-smoke-tests')


@pytest.fixture
def mock_redis():
    """Mock Redis connection to avoid needing Redis running."""
    with patch('core.redis.get_redis_connection') as mock:
        mock_conn = MagicMock()
        mock.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_rq_queue(mock_redis):
    """Mock RQ queue to avoid actual job queuing."""
    with patch('rq.Queue') as mock_queue_class:
        mock_queue = MagicMock()
        mock_job = MagicMock()
        mock_job.id = 'test-job-123'
        mock_queue.enqueue.return_value = mock_job
        mock_queue_class.return_value = mock_queue
        yield mock_queue


@pytest.fixture
def mock_openai():
    """Mock OpenAI API calls."""
    with patch('openai.OpenAI') as mock:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '''
        {
            "outfits": [
                {
                    "items": [
                        {"name": "White T-Shirt", "category": "tops"},
                        {"name": "Blue Jeans", "category": "bottoms"}
                    ],
                    "styling_notes": "Classic casual look",
                    "why_it_works": "Timeless combination",
                    "confidence_level": "Comfort Zone",
                    "vibe_keywords": ["casual", "classic"]
                }
            ]
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        mock.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_s3():
    """Mock S3 storage operations."""
    with patch('services.storage.s3_storage.S3Storage') as mock:
        mock_storage = MagicMock()
        mock_storage.upload_file.return_value = 'https://s3.example.com/test.jpg'
        mock_storage.get_file_url.return_value = 'https://s3.example.com/test.jpg'
        mock.return_value = mock_storage
        yield mock_storage


@pytest.fixture
def mock_wardrobe_data():
    """Mock wardrobe data for testing."""
    return {
        "items": [
            {
                "id": "item_001",
                "styling_details": {
                    "name": "White T-Shirt",
                    "category": "tops",
                    "colors": ["white"],
                    "description": "Basic white cotton t-shirt"
                },
                "usage_metadata": {"times_worn": 5},
                "system_metadata": {"image_path": "wardrobe_photos/item_001.jpg"}
            },
            {
                "id": "item_002",
                "styling_details": {
                    "name": "Blue Jeans",
                    "category": "bottoms",
                    "colors": ["blue"],
                    "description": "Classic blue denim jeans"
                },
                "usage_metadata": {"times_worn": 10},
                "system_metadata": {"image_path": "wardrobe_photos/item_002.jpg"}
            }
        ],
        "count": 2
    }


@pytest.fixture
def client(mock_redis, mock_rq_queue):
    """FastAPI test client with mocked dependencies."""
    from fastapi.testclient import TestClient
    from main import app

    with TestClient(app) as test_client:
        yield test_client

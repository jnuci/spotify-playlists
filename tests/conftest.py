import pytest
from datetime import datetime, timedelta
from main import create_app

@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"]=True
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess['access_token'] = 'test_access_token'
            sess['refresh_token'] = 'test_refresh_token'
            sess['expires_at'] = (datetime.now() + timedelta(hours=1)).timestamp()
        yield client
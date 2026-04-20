import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

from app import create_app

app = create_app()
app.testing = True

with app.test_client() as client:
    with client.session_transaction() as sess:
        sess['user_id'] = 1  # Fake user session to bypass login_required
        sess['username'] = 'testuser'

    print("Testing /spaces...")
    resp = client.get('/spaces')
    print("Status:", resp.status_code)
    if resp.status_code != 200:
        print(resp.data.decode('utf-8'))

    print("Testing /space/1...")
    resp2 = client.get('/space/1')
    print("Status:", resp2.status_code)
    if resp2.status_code != 200:
        print(resp2.data.decode('utf-8'))

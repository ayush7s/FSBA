import sys
from app import app

with app.app_context():
    with app.test_client() as client:
        try:
            response = client.get('/')
            print(f"Status Code: {response.status_code}")
            if response.status_code != 200:
                print(f"Response: {response.get_data(as_text=True)[:500]}")
        except Exception as e:
            print(f"Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()

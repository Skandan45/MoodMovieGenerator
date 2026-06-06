import requests, json, sys
url = 'http://127.0.0.1:5000/api/movies/mood/happy?lang=en'
try:
    resp = requests.get(url, timeout=10)
    print('Status:', resp.status_code)
    print('Body:', resp.text[:500])
except Exception as e:
    print('Error:', e)
    sys.exit(1)

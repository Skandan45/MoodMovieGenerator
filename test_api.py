import requests, json, sys
url = 'http://127.0.0.1:5000/api/movies/mood/happy?mood_prompt=test'
try:
    r = requests.get(url, timeout=10)
    print('status', r.status_code)
    print('text', r.text[:500])
except Exception as e:
    print('error', e)
    sys.exit(1)

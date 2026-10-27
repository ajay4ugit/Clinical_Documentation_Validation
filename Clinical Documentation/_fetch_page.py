"""Fetch one page and print the full error body."""
import urllib.request, sys

try:
    r = urllib.request.urlopen("http://127.0.0.1:8082/")
    print("SUCCESS", r.status)
    print(r.read().decode()[:500])
except urllib.error.HTTPError as e:
    print("HTTP", e.code)
    print(e.read().decode()[:3000])
except Exception as e:
    print("CONN ERROR:", e)

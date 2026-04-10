import ssl
import urllib.request
import certifi

print("OPENSSL:", ssl.OPENSSL_VERSION)
print("CERT FILE:", certifi.where())

url = "https://www.naver.com"

context = ssl.create_default_context(cafile=certifi.where())

with urllib.request.urlopen(url, context=context, timeout=10) as r:
    print("STATUS:", r.status)
    print("OK")
import base64
import hashlib

with open('app.py') as f:
    app_py = f.read()

with open('mask_bg_48.png', 'rb') as f:
    dl48 = f.read()

print('Downloaded 48 hash:', hashlib.sha256(dl48).hexdigest())

b48_b64 = None
for line in app_py.split('\n'):
    if 'b48 = base64.b64decode' in line:
        b48_b64 = line.split('"')[1]
if b48_b64:
    b48 = base64.b64decode(b48_b64)
    print('Embedded 48 hash:  ', hashlib.sha256(b48).hexdigest())

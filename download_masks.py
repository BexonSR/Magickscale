"""
Download the real RGBA Gemini watermark masks from journey-ad's repo via GitHub API (blob download).
"""
import urllib.request, ssl, json, base64, struct, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_blob_b64(owner, repo, path):
    # First get the SHA of the file
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    meta = json.loads(urllib.request.urlopen(req, context=ctx).read().decode())
    # Now get the blob
    blob_url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{meta['sha']}"
    req2 = urllib.request.Request(blob_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.raw'})
    data = urllib.request.urlopen(req2, context=ctx).read()
    return data, meta['sha']

# Try to get actual PNG from the journey-ad repo (different owner, might have RGBA masks)
repos = [
    ('journey-ad', 'gemini-watermark-remover', 'src/assets/bg_48.png'),
    ('journey-ad', 'gemini-watermark-remover', 'src/assets/bg_96.png'),
]

for owner, repo, path in repos:
    try:
        data, sha = get_blob_b64(owner, repo, path)
        fname = os.path.basename(path)
        with open(f'mask_{fname}', 'wb') as f:
            f.write(data)
        
        # Check PNG header and color type
        if data[:4] == b'\x89PNG':
            w = struct.unpack('>I', data[16:20])[0]
            h = struct.unpack('>I', data[20:24])[0]
            color_type = data[25]
            print(f'{fname}: {w}x{h} color_type={color_type} (6=RGBA, 2=RGB) size={len(data)}')
        else:
            print(f'{fname}: NOT a PNG!')
    except Exception as e:
        print(f'Failed {path}: {e}')

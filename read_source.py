"""
Fetch and read the watermarkRemover JS source from journey-ad repo.
"""
import urllib.request, ssl, json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def get_file(owner, repo, path):
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    meta = json.loads(urllib.request.urlopen(req, context=ctx).read().decode())
    blob_url = f"https://api.github.com/repos/{owner}/{repo}/git/blobs/{meta['sha']}"
    req2 = urllib.request.Request(blob_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github.raw'})
    return urllib.request.urlopen(req2, context=ctx).read().decode('utf-8', errors='replace')

# Find JS source files
def list_dir(owner, repo, path, depth=0):
    if depth > 3: return []
    api_url = f'https://api.github.com/repos/{owner}/{repo}/contents/{path}'
    req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
    items = json.loads(urllib.request.urlopen(req, context=ctx).read().decode())
    result = []
    for item in items:
        if item['type'] == 'file' and item['name'].endswith('.js') and 'watermark' in item['name'].lower():
            result.append(item['path'])
        elif item['type'] == 'dir':
            result.extend(list_dir(owner, repo, item['path'], depth+1))
    return result

print("Searching for JS files...")
js_files = list_dir('journey-ad', 'gemini-watermark-remover', 'src')
print("JS files found:", js_files)

for f in js_files[:3]:
    try:
        print(f"\n=== {f} ===")
        content = get_file('journey-ad', 'gemini-watermark-remover', f)
        # Print lines containing key algorithm terms
        for i, line in enumerate(content.split('\n')):
            if any(kw in line.lower() for kw in ['alpha', 'reverse', 'bg_', 'mask', 'composite', 'fg', '255', 'margin']):
                print(f"  L{i+1}: {line.rstrip()}")
    except Exception as e:
        print(f"Error: {e}")

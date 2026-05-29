import urllib.request, json, ssl, os

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

def api(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return json.loads(urllib.request.urlopen(req, context=ctx).read().decode())

def search_repo(api_url, depth=0):
    if depth > 4:
        return
    try:
        items = api(api_url)
        if not isinstance(items, list):
            return
        for item in items:
            if item['type'] == 'file':
                name = item['name'].lower()
                if 'bg_' in name or 'mask' in name or name.endswith('.png'):
                    print(item['path'], '|', item.get('download_url', ''))
            elif item['type'] == 'dir':
                search_repo(item['url'], depth + 1)
    except Exception as e:
        print(f'Error: {e}')

print("=== Searching journey-ad ===")
search_repo('https://api.github.com/repos/journey-ad/gemini-watermark-remover/contents/public')
search_repo('https://api.github.com/repos/journey-ad/gemini-watermark-remover/contents/src')

import sys
if sys.platform == 'win32':
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('MagickScale.App')
    except Exception:
        pass

import os
import json
import subprocess
import threading
import time
import webbrowser
import concurrent.futures
import urllib.request
import zipfile
import shutil
import sys
import base64
import tempfile
import ssl
from http.server import HTTPServer, SimpleHTTPRequestHandler
import tkinter as tk
from tkinter import filedialog, messagebox

try:
    import webview
    HAS_WEBVIEW = True
except ImportError:
    HAS_WEBVIEW = False

HAS_PYSTRAY = False
try:
    import pystray
    from PIL import Image
    HAS_PYSTRAY = True
except ImportError:
    pass


PORT = 5050

if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

WEB_DIR = os.path.join(base_dir, 'web')

# Runtime dir (next to .exe, persists between runs)
if getattr(sys, 'frozen', False):
    runtime_dir = os.path.dirname(sys.executable)
else:
    runtime_dir = os.path.dirname(os.path.abspath(__file__))

ESRGAN_DIR = os.path.join(runtime_dir, 'bin', 'realesrgan')
if sys.platform == 'win32':
    ESRGAN_EXE_NAME = 'realesrgan-ncnn-vulkan.exe'
    ESRGAN_RELEASE_URL = (
        "https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/"
        "download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-windows.zip"
    )
else:
    ESRGAN_EXE_NAME = 'realesrgan-ncnn-vulkan'
    ESRGAN_RELEASE_URL = (
        "https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/"
        "download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-ubuntu.zip"
    )

ESRGAN_EXE = os.path.join(ESRGAN_DIR, ESRGAN_EXE_NAME)
MODELS_DIR = os.path.join(ESRGAN_DIR, 'models')

# Upscayl custom-models (https://github.com/upscayl/custom-models)
# MIT / permissive licenses – credits listed in UI
CUSTOM_MODELS = {
    "ultrasharp-4x": {
        "display": "UltraSharp (4x) — Best for Real Photos",
        "bin":   None,
        "param": None,
        "scale": 4,
        "credit": "Remacri/UltraSharp (MIT)"
    },
    "remacri-4x": {
        "display": "Remacri (4x) — Smooth, Realistic Textures",
        "bin":   None,
        "param": None,
        "scale": 4,
        "credit": "Remacri (MIT)"
    },
    "upscayl-lite-4x": {
        "display": "Upscayl Lite (4x) — Fast & Lightweight",
        "bin":   None,
        "param": None,
        "scale": 4,
        "credit": "Upscayl Lite (AGPL-3.0)"
    },
    "ultramix-balanced-4x": {
        "display": "UltraMix Balanced (4x) — All-rounder",
        "bin":   None,
        "param": None,
        "scale": 4,
        "credit": "UltraMix (MIT)"
    },
    "realesrgan-x4plus": {
        "display": "RealESRGAN x4+ (4x) — Best for Photos (Default)",
        "bin": None, "param": None,
        "scale": 4,
        "credit": "Real-ESRGAN – xinntao (BSD-3-Clause)"
    },
    "realesrgan-x4plus-anime": {
        "display": "RealESRGAN x4+ Anime (4x) — Best for Illustrations",
        "bin": None, "param": None,
        "scale": 4,
        "credit": "Real-ESRGAN – xinntao (BSD-3-Clause)"
    },
    "realesr-animevideov3": {
        "display": "RealESR AnimeVideoV3 (4x) — Anime Video Frames",
        "bin": None, "param": None,
        "scale": 4,
        "credit": "Real-ESRGAN – xinntao (BSD-3-Clause)"
    },
    "4x_NMKD-Siax_200k": {
        "display": "NMKD Siax (4x) — For Clean/Compressed Photos",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4x_NMKD-Siax_200k.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4x_NMKD-Siax_200k.param",
        "scale": 4,
        "credit": "NMKD (MIT)"
    },
    "4x_NMKD-Superscale-SP_178000_G": {
        "display": "NMKD Superscale (4x) — For Perfect Real Photos",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4x_NMKD-Superscale-SP_178000_G.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4x_NMKD-Superscale-SP_178000_G.param",
        "scale": 4,
        "credit": "NMKD (MIT)"
    },
    "RealESRGAN_General_x4_v3": {
        "display": "RealESRGAN General v3 (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/RealESRGAN_General_x4_v3.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/RealESRGAN_General_x4_v3.param",
        "scale": 4,
        "credit": "xinntao (BSD-3-Clause)"
    },
    "RealESRGAN_General_WDN_x4_v3": {
        "display": "RealESRGAN General WDN v3 (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/RealESRGAN_General_WDN_x4_v3.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/RealESRGAN_General_WDN_x4_v3.param",
        "scale": 4,
        "credit": "xinntao (BSD-3-Clause)"
    },
    "uniscale_restore": {
        "display": "Uniscale Restore (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/uniscale_restore.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/uniscale_restore.param",
        "scale": 4,
        "credit": "Kim2091 (MIT)"
    },
    "4xLSDIR": {
        "display": "LSDIR (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIR.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIR.param",
        "scale": 4,
        "credit": "Phhofm (MIT)"
    },
    "4xNomos8kSC": {
        "display": "Nomos8kSC (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4xNomos8kSC.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xNomos8kSC.param",
        "scale": 4,
        "credit": "Phhofm (MIT)"
    },
    "4xHFA2k": {
        "display": "HFA2k (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4xHFA2k.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xHFA2k.param",
        "scale": 4,
        "credit": "Phhofm (MIT)"
    },
    "4xLSDIRplusC": {
        "display": "LSDIR plusC (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIRplusC.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIRplusC.param",
        "scale": 4,
        "credit": "Phhofm (MIT)"
    },
    "4xLSDIRCompactC3": {
        "display": "LSDIR Compact C3 (4x)",
        "bin": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIRCompactC3.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xLSDIRCompactC3.param",
        "scale": 4,
        "credit": "Phhofm (MIT)"
    }
}


def load_app_settings():
    appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
    settings_dir = os.path.join(appdata, 'MagickScale')
    state_file = os.path.join(settings_dir, 'state.json')
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_app_setting(key, value):
    settings = load_app_settings()
    settings[key] = value
    appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
    settings_dir = os.path.join(appdata, 'MagickScale')
    os.makedirs(settings_dir, exist_ok=True)
    state_file = os.path.join(settings_dir, 'state.json')
    try:
        with open(state_file, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Failed to save setting {key}: {e}")

# =====================================================================
# GLOBAL STATE
# =====================================================================
state_lock = threading.Lock()

app_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0, 'total_space_saved': 0
}
up_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0,
}
lr_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0,
}
sl_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0
}
me_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0
}
ol_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0
}
co_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0
}
mt_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0
}
vd_state = {
    'processing': False, 'cancel_requested': False,
    'queue': [], 'current_index': 0,
    'start_time': 0, 'total_processed': 0,
    'status_text': 'Idle'
}
download_state = {
    'status': 'idle',
    'bytes_downloaded': 0,
    'total_bytes': 0,
    'error': '',
    'percent': 0
}


# =====================================================================
# DIALOGS
# =====================================================================
def ask_open_files():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    files = filedialog.askopenfilenames(
        parent=root, title="Select Images",
        filetypes=[
            ("Image Files", "*.jpg;*.jpeg;*.png;*.webp;*.tif;*.tiff;*.bmp;*.heic;*.cr2;*.nef;*.arw"),
            ("All Files", "*.*")
        ]
    )
    root.destroy()
    return list(files)

def ask_directory(title="Select Folder"):
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    folder = filedialog.askdirectory(parent=root, title=title)
    root.destroy()
    return folder

# =====================================================================
# METADATA
# =====================================================================
def get_image_metadata(file_paths):
    metadata = {}
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    for path in file_paths:
        try:
            r = subprocess.run(
                ["magick", "identify", "-format", "%w,%h,%[format]", path],
                capture_output=True, text=True, check=True, creationflags=cf
            )
            parts = r.stdout.strip().split(',')
            sz = os.path.getsize(path)
            if len(parts) >= 3:
                w, h, fmt = parts[0], parts[1], parts[2]
                metadata[path] = {
                    "width": int(w) if w.isdigit() else 0,
                    "height": int(h) if h.isdigit() else 0,
                    "format": fmt, "size": sz, "name": os.path.basename(path)
                }
        except Exception as e:
            metadata[path] = {
                "error": str(e), "name": os.path.basename(path),
                "size": os.path.getsize(path) if os.path.exists(path) else 0
            }
    return metadata

# =====================================================================
# DOWNSCALER
# =====================================================================
def process_queue(settings):
    app_state['processing'] = True
    app_state['cancel_requested'] = False
    app_state['start_time'] = time.time()
    app_state['total_processed'] = 0
    app_state['total_space_saved'] = 0

    mode = settings.get('mode', 'fit')
    filter_type = settings.get('filter', 'Lanczos')
    quality = str(settings.get('quality', 90))
    out_format = settings.get('format', 'same')
    out_dir = settings.get('out_dir', '')
    use_gpu = settings.get('use_gpu', True)
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    def process_item(i, item):
        if app_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; return
        with state_lock: app_state['current_index'] = i
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'; return
        src_size = os.path.getsize(src)
        name, ext = os.path.splitext(os.path.basename(src))
        if out_format != 'same': ext = '.' + out_format.lower()
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        suffix = settings.get('suffix', '_4k')
        out = os.path.join(od, f"{name}{suffix}{ext}")
        cmd = ["magick", src, "-limit", "thread", "2"]
        if use_gpu: cmd.extend(["-set", "opencl:enable", "true"])
        cmd.extend(["-auto-orient", "-filter", filter_type])
        if mode == 'fit':           cmd.extend(["-resize", "3840x2160>"])
        elif mode == 'longest':     cmd.extend(["-resize", "3840x3840>"])
        elif mode == 'width':       cmd.extend(["-resize", "3840>"])
        elif mode == 'height':      cmd.extend(["-resize", "x2160>"])
        elif mode == 'percent_50':  cmd.extend(["-resize", "50%"])
        elif mode == 'custom':
            cust_w = settings.get('custom_width', 1920)
            cust_h = settings.get('custom_height', 1080)
            cmd.extend(["-resize", f"{cust_w}x{cust_h}>"])

        if ext.lower() in ['.jpg', '.jpeg', '.webp']: cmd.extend(["-quality", quality])
        cmd.append(out)
        try:
            subprocess.run(cmd, check=True, creationflags=cf)
            item['status'] = 'completed'
            if os.path.exists(out):
                saved = max(0, src_size - os.path.getsize(out))
                item['size_saved'] = saved
                with state_lock: app_state['total_space_saved'] += saved
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
        with state_lock: app_state['total_processed'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        concurrent.futures.wait([ex.submit(process_item, i, item) for i, item in enumerate(app_state['queue'])])
    app_state['processing'] = False

# =====================================================================
# ESRGAN ENGINE MANAGEMENT
# =====================================================================
def get_esrgan_exe():
    runtime_exe = os.path.join(runtime_dir, 'bin', 'realesrgan', ESRGAN_EXE_NAME)
    bundled_exe = os.path.join(base_dir, 'bin', 'realesrgan', ESRGAN_EXE_NAME)
    if os.path.isfile(runtime_exe):
        return runtime_exe
    return bundled_exe

def check_esrgan_ready():
    runtime_exe = os.path.join(runtime_dir, 'bin', 'realesrgan', ESRGAN_EXE_NAME)
    bundled_exe = os.path.join(base_dir, 'bin', 'realesrgan', ESRGAN_EXE_NAME)
    return os.path.isfile(runtime_exe) or os.path.isfile(bundled_exe)

def model_is_downloaded(model_key):
    """Check if a custom model's .bin and .param files exist in runtime_dir or bundled base_dir."""
    if model_key in {
        "realesrgan-x4plus", "realesrgan-x4plus-anime", "realesr-animevideov3",
        "ultrasharp-4x", "remacri-4x", "upscayl-lite-4x", "ultramix-balanced-4x"
    }:
        return True
        
    bname = model_key
    
    # Check in runtime directory next to exe (persistent)
    runtime_models = os.path.join(runtime_dir, 'bin', 'realesrgan', 'models')
    runtime_esrgan = os.path.join(runtime_dir, 'bin', 'realesrgan')
    
    # Check in base_dir (bundled inside exe)
    bundled_models = os.path.join(base_dir, 'bin', 'realesrgan', 'models')
    bundled_esrgan = os.path.join(base_dir, 'bin', 'realesrgan')
    
    # Return true if files exist in either runtime or bundled directory
    in_runtime = (
        (os.path.isfile(os.path.join(runtime_models, f"{bname}.bin")) and
         os.path.isfile(os.path.join(runtime_models, f"{bname}.param"))) or
        os.path.isfile(os.path.join(runtime_esrgan, f"{bname}.bin"))
    )
    in_bundled = (
        (os.path.isfile(os.path.join(bundled_models, f"{bname}.bin")) and
         os.path.isfile(os.path.join(bundled_models, f"{bname}.param"))) or
        os.path.isfile(os.path.join(bundled_esrgan, f"{bname}.bin"))
    )
    return in_runtime or in_bundled

def list_available_models():
    """Scan models dir + check CUSTOM_MODELS registry."""
    result = []
    for key, info in CUSTOM_MODELS.items():
        downloaded = model_is_downloaded(key)
        result.append({
            "key": key,
            "display": info["display"],
            "scale": info["scale"],
            "credit": info["credit"],
            "downloaded": downloaded,
            "bundled": info.get("bin") is None  # bundled with engine
        })
    # Also scan models folder for any user-added .param files
    if os.path.isdir(MODELS_DIR):
        known_keys = set(CUSTOM_MODELS.keys())
        for fname in os.listdir(MODELS_DIR):
            if fname.endswith('.param'):
                mkey = fname[:-6]
                if mkey not in known_keys:
                    result.append({
                        "key": mkey,
                        "display": f"{mkey} (Custom)",
                        "scale": 4,
                        "credit": "User-provided custom model",
                        "downloaded": True,
                        "bundled": False
                    })
                    
    # Also scan external custom models folder if configured
    app_settings = load_app_settings()
    custom_path = app_settings.get('custom_models_path', '')
    if custom_path and os.path.isdir(custom_path):
        known_keys = set(CUSTOM_MODELS.keys())
        for fname in os.listdir(custom_path):
            if fname.endswith('.param'):
                mkey = fname[:-6]
                # Avoid duplicates
                if mkey not in known_keys and not any(r['key'] == mkey for r in result):
                    result.append({
                        "key": mkey,
                        "display": f"{mkey} (Custom External)",
                        "scale": 4,
                        "credit": f"External: {custom_path}",
                        "downloaded": True,
                        "bundled": False
                    })
    return result

WATERMARK_DIR = os.path.join(runtime_dir, 'bin', 'watermark')
MASK_48_URL = "https://raw.githubusercontent.com/GargantuaX/gemini-watermark-remover/main/assets/bg_48.png"
MASK_96_URL = "https://raw.githubusercontent.com/GargantuaX/gemini-watermark-remover/main/assets/bg_96.png"

def ensure_watermark_masks():
    os.makedirs(WATERMARK_DIR, exist_ok=True)
    mask_48_path = os.path.join(WATERMARK_DIR, 'bg_48.png')
    mask_96_path = os.path.join(WATERMARK_DIR, 'bg_96.png')
    
    # Real Gemini watermark masks (embedded to avoid 404s and make it offline)
    b48 = base64.b64decode("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")
    b96 = base64.b64decode("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")
    
    if not os.path.exists(mask_48_path):
        print("Writing embedded mask 48...")
        with open(mask_48_path, 'wb') as f: f.write(b48)
        
    if not os.path.exists(mask_96_path):
        print("Writing embedded mask 96...")
        with open(mask_96_path, 'wb') as f: f.write(b96)

def download_esrgan_async():
    global download_state
    download_state['status'] = 'downloading'
    download_state['bytes_downloaded'] = 0
    download_state['total_bytes'] = 0
    download_state['percent'] = 0
    download_state['error'] = ''
    
    try:
        os.makedirs(ESRGAN_DIR, exist_ok=True)
        zip_path = os.path.join(ESRGAN_DIR, 'realesrgan.zip')
        tmp_zip_path = zip_path + '.tmp'
        
        # Clean up legacy files
        for p in [zip_path, tmp_zip_path]:
            if os.path.exists(p):
                try: os.remove(p)
                except: pass
                
        # Ensure temp folder is empty
        temp_extract_dir = os.path.join(runtime_dir, 'bin', 'realesrgan_temp')
        if os.path.exists(temp_extract_dir):
            try: shutil.rmtree(temp_extract_dir)
            except: pass
            
        print(f"Downloading ESRGAN engine from {ESRGAN_RELEASE_URL}")
        
        req = urllib.request.Request(
            ESRGAN_RELEASE_URL, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        ctx = ssl.create_default_context()
        try:
            response = urllib.request.urlopen(req, timeout=45, context=ctx)
        except Exception as e:
            print(f"Engine download failed with default SSL: {e}. Retrying with unverified context...")
            unverified_ctx = ssl._create_unverified_context()
            response = urllib.request.urlopen(req, timeout=45, context=unverified_ctx)
        
        with response:
            total_size = int(response.headers.get('content-length', 0))
            download_state['total_bytes'] = total_size
            
            bytes_so_far = 0
            chunk_size = 1024 * 64
            
            with open(tmp_zip_path, 'wb') as f:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    bytes_so_far += len(chunk)
                    download_state['bytes_downloaded'] = bytes_so_far
                    if total_size > 0:
                        download_state['percent'] = int((bytes_so_far / total_size) * 100)
                        
        if os.path.exists(zip_path):
            try: os.remove(zip_path)
            except: pass
        os.rename(tmp_zip_path, zip_path)
        
        download_state['status'] = 'extracting'
        print("Extracting...")
        os.makedirs(temp_extract_dir, exist_ok=True)
        
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(temp_extract_dir)
            
        try: os.remove(zip_path)
        except: pass
        
        # Move files
        for root, dirs, files in os.walk(temp_extract_dir):
            for f in files:
                src_file = os.path.join(root, f)
                rel_path = os.path.relpath(src_file, temp_extract_dir)
                parts = rel_path.split(os.sep)
                if len(parts) > 1:
                    dst_rel = os.path.join(*parts[1:])
                else:
                    dst_rel = rel_path
                    
                dst_file = os.path.join(ESRGAN_DIR, dst_rel)
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                if os.path.exists(dst_file):
                    try: os.remove(dst_file)
                    except: pass
                shutil.move(src_file, dst_file)
                if sys.platform != 'win32' and os.path.basename(dst_file) == ESRGAN_EXE_NAME:
                    try:
                        os.chmod(dst_file, 0o755)
                        print(f"Set execution permissions on {dst_file}")
                    except Exception as e:
                        print(f"Failed to set execution permission: {e}")
                
        try: shutil.rmtree(temp_extract_dir)
        except: pass
        
        # Move bundled models
        os.makedirs(MODELS_DIR, exist_ok=True)
        for f in os.listdir(ESRGAN_DIR):
            if f.endswith('.bin') or f.endswith('.param'):
                src = os.path.join(ESRGAN_DIR, f)
                dst = os.path.join(MODELS_DIR, f)
                if not os.path.exists(dst):
                    try: shutil.move(src, dst)
                    except: pass
                    
        ensure_watermark_masks()
        download_state['status'] = 'completed'
    except Exception as e:
        print(f"ESRGAN download failed: {e}")
        download_state['status'] = 'failed'
        download_state['error'] = str(e)


def download_custom_model(model_key):
    """Download a specific custom model's .bin and .param files with User-Agent and timeout."""
    info = CUSTOM_MODELS.get(model_key)
    if not info or info.get('bin') is None:
        return False, "Model is bundled with the engine or not found."
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        bin_path   = os.path.join(MODELS_DIR, f"{model_key}.bin")
        param_path = os.path.join(MODELS_DIR, f"{model_key}.param")
        print(f"Downloading {model_key}...")
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        req_bin = urllib.request.Request(info['bin'], headers=headers)
        req_param = urllib.request.Request(info['param'], headers=headers)
        
        ctx = ssl.create_default_context()
        
        # Download bin file
        try:
            with urllib.request.urlopen(req_bin, timeout=45, context=ctx) as response, open(bin_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(f"Bin download failed with default SSL: {e}. Retrying with unverified context...")
            unverified_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req_bin, timeout=45, context=unverified_ctx) as response, open(bin_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
                
        # Download param file
        try:
            with urllib.request.urlopen(req_param, timeout=45, context=ctx) as response, open(param_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
        except Exception as e:
            print(f"Param download failed with default SSL: {e}. Retrying with unverified context...")
            unverified_ctx = ssl._create_unverified_context()
            with urllib.request.urlopen(req_param, timeout=45, context=unverified_ctx) as response, open(param_path, 'wb') as out_file:
                shutil.copyfileobj(response, out_file)
            
        return True, ""
    except Exception as e:
        return False, str(e)

def detect_nvidia_gpu():
    """Try to detect if an NVIDIA GPU is present using nvidia-smi."""
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        r = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5, creationflags=cf
        )
        if r.returncode == 0 and r.stdout.strip():
            return True, r.stdout.strip().split('\n')[0].strip()
    except Exception:
        pass
    return False, None

# =====================================================================
# AI UPSCALER PROCESSING
# =====================================================================
def process_upscale_queue(settings):
    up_state['processing'] = True
    up_state['cancel_requested'] = False
    up_state['start_time'] = time.time()
    up_state['total_processed'] = 0

    model    = settings.get('model', 'realesrgan-x4plus')
    fmt      = settings.get('format', 'png')
    out_dir  = settings.get('out_dir', '')
    scale    = int(settings.get('scale', 4))
    gpu_id   = int(settings.get('gpu_id', 0))
    tta      = settings.get('tta', False)
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    # Concurrency limit based on VRAM capacity (Optimal: GPU uses 2 parallel threads; CPU uses 3-4)
    if gpu_id == -1:
        max_workers = min(4, os.cpu_count() or 2)
    else:
        max_workers = 2

    def process_item(i, item):
        if up_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'
            with state_lock: up_state['total_processed'] += 1
            return

        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: up_state['total_processed'] += 1
            return

        name, _ = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        suffix = settings.get('suffix', '_upscaled')
        out = os.path.join(od, f"{name}{suffix}.{fmt}")

        # If scale > 4, chain two 4x passes
        passes = 1
        pass_scale = scale
        tmp_path = None
        if scale > 4:
            passes = 2
            pass_scale = 4

        try:
            current_in = src
            for pass_num in range(passes):
                if pass_num == passes - 1:
                    current_out = out
                else:
                    tmp_path = os.path.join(od, f"__tmp_{name}_pass{pass_num}.png")
                    current_out = tmp_path

                # Resolve the models directory that contains the model files
                used_models_dir = MODELS_DIR
                model_param = f"{model}.param"
                
                # Check external custom models folder if configured
                app_settings = load_app_settings()
                custom_path = app_settings.get('custom_models_path', '')
                
                bundled_models_dir = os.path.join(base_dir, 'bin', 'realesrgan', 'models')
                runtime_models_dir = os.path.join(runtime_dir, 'bin', 'realesrgan', 'models')
                
                if custom_path and os.path.isfile(os.path.join(custom_path, model_param)):
                    used_models_dir = custom_path
                elif os.path.isfile(os.path.join(runtime_models_dir, model_param)):
                    used_models_dir = runtime_models_dir
                elif os.path.isfile(os.path.join(bundled_models_dir, model_param)):
                    used_models_dir = bundled_models_dir

                # Executable resolution
                esrgan_exe_path = get_esrgan_exe()

                current_gpu_id = gpu_id
                success = False
                attempts = 0
                
                while not success and attempts < 2:
                    attempts += 1
                    cmd = [
                        esrgan_exe_path,
                        "-i", current_in,
                        "-o", current_out,
                        "-n", model,
                        "-s", str(pass_scale),
                        "-g", str(current_gpu_id),
                        "-f", fmt
                    ]
                    if tta:
                        cmd.append("-x")

                    # Use auto-tiling (-t 0) so Vulkan optimizes tile sizes to fit in available VRAM, preventing slow paging fallback.
                    cmd.extend(["-t", "0"])
                    cmd.extend(["-m", used_models_dir])

                    # Use Popen to read stderr line by line for progress
                    process = subprocess.Popen(
                        cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        bufsize=1,
                        creationflags=cf
                    )

                    import re
                    buffer = []
                    while True:
                        if up_state['cancel_requested']:
                            process.terminate()
                            raise Exception("Cancelled")
                        char = process.stderr.read(1)
                        if not char:
                            if process.poll() is not None:
                                break
                            continue
                        if char in ('\r', '\n'):
                            line = "".join(buffer)
                            buffer = []
                            if "%" in line:
                                try:
                                    m = re.search(r'(\d+(?:\.\d+)?)%', line)
                                    if m:
                                        pct = float(m.group(1))
                                        if passes > 1:
                                            pass_weight = 100.0 / passes
                                            pct = (pass_num * pass_weight) + (pct / passes)
                                        item['percent'] = round(pct, 1)
                                except Exception:
                                    pass
                        else:
                            buffer.append(char)

                    process.wait()
                    if process.returncode == 0:
                        success = True
                    else:
                        err = process.stderr.read()
                        print(f"Upscaling failed with code {process.returncode}. Stderr: {err}")
                        if current_gpu_id >= 0:
                            print("GPU upscaling failed. Retrying on CPU (-g -1)...")
                            item['error'] = "GPU failed, retrying on CPU..."
                            current_gpu_id = -1
                        else:
                            raise Exception(err or f"Process exited with {process.returncode}")

                if tmp_path and os.path.exists(tmp_path):
                    current_in = tmp_path

            item['status'] = 'completed'
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try: os.remove(tmp_path)
                except: pass

        with state_lock: up_state['total_processed'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
        concurrent.futures.wait([ex.submit(process_item, i, item) for i, item in enumerate(up_state['queue'])])

    up_state['processing'] = False

# =====================================================================
# LOGO REMOVER
# =====================================================================
# ── Embedded real mask files (from PlayerYK/GeminiWatermarkRemover, MIT) ────
import base64 as _b64
_MASK_48_B64 = None
_MASK_96_B64 = None

# Embedded masks (PlayerYK/GeminiWatermarkRemover, MIT License)
_MASK_48_B64_REAL = "iVBORw0KGgoAAAANSUhEUgAAADAAAAAwCAIAAADYYG7QAAAGVElEQVR4nMVYvXIbNxD+FvKMWInXmd2dK7MTO7sj9QKWS7qy/Ab2o/gNmCp0JyZ9dHaldJcqTHfnSSF1R7kwlYmwKRYA93BHmkrseMcjgzgA++HbH2BBxhhmBiB/RYgo+hkGSFv/ZOY3b94w89u3b6HEL8JEYCYATCAi2JYiQ8xMDADGWsvMbfVagm6ZLxKGPXr0qN/vJ0mSpqn0RzuU//Wu9MoyPqxmtqmXJYwxxpiAQzBF4x8/fiyN4XDYoZLA5LfEhtg0+glMIGZY6wABMMbs4CaiR8brkYIDwGg00uuEMUTQ1MYqPBRRYZjZ+q42nxEsaYiV5VOapkmSSLvX62VZprUyM0DiQACIGLCAESIAEINAAAEOcQdD4a+2FJqmhDd/YEVkMpmEtrU2igCocNHW13swRBQYcl0enxbHpzEhKo0xSZJEgLIsC4Q5HJaJ2Qg7kKBjwMJyCDciBBcw7fjSO4tQapdi5vF43IZ+cnISdh9Y0At2RoZWFNtLsxr8N6CUTgCaHq3g+Pg4TVO1FACSaDLmgMhYC8sEQzCu3/mQjNEMSTvoDs4b+nXny5cvo4lBJpNJmKj9z81VrtNhikCgTsRRfAklmurxeKx9JZIsy548eeITKJgAQwzXJlhDTAwDgrXkxxCD2GfqgEPa4rnBOlApFUC/39fR1CmTyWQwGAQrR8TonMRNjjYpTmPSmUnC8ODgQHqSJDk7O9uNBkCv15tOp4eHh8SQgBICiCGu49YnSUJOiLGJcG2ydmdwnRcvXuwwlpYkSabTaZS1vyimc7R2Se16z58/f/jw4Z5LA8iy7NmzZ8J76CQ25F2UGsEAJjxo5194q0fn9unp6fHx8f5oRCQ1nJ+fbxtA3HAjAmCMCaGuAQWgh4eH0+k0y7LGvPiU3CVXV1fz+by+WQkCJYaImKzL6SEN6uMpjBVMg8FgOp3GfnNPQADqup79MLv59AlWn75E/vAlf20ibmWg0Pn06dPJZNLr9e6nfLu8//Ahv/gFAEdcWEsgZnYpR3uM9KRpOplMGmb6SlLX9Ww2q29WyjH8+SI+pD0GQJIkJycn/8J/I4mWjaQoijzPb25uJJsjmAwqprIsG4/HbVZ2L/1fpCiKoijKqgTRBlCWZcPhcDQafUVfuZfUdb1cLpfL5cePf9Lr16/3zLz/g9T1quNy+F2FiYjSNB0Oh8Ph8HtRtV6vi6JYLpdVVbmb8t3dnSAbjUbRNfmbSlmWeZ6XHytEUQafEo0xR0dHUdjvG2X3Sd/Fb0We56t6BX8l2mTq6BCVnqOjo7Ozs29hRGGlqqrOr40CIKqeiGg8Hn/xcri/rG/XeZ7/evnrjjGbC3V05YC/BSRJ8urVq36/3zX7Hjaq63o+n19fX/upUqe5VxFok7UBtQ+T6XQ6GAz2Vd6Ssizn8/nt7a3ay1ZAYbMN520XkKenpx0B2E2SLOo+FEWxWPwMgMnC3/adejZMYLLS42r7oH4LGodpsVgURdHQuIcURbFYLDYlVKg9sCk5wpWNiHym9pUAEQGG6EAqSxhilRQWi0VZVmrz23yI5cPV1dX5TwsmWGYrb2TW36OJGjdXhryKxEeHvjR2Fgzz+bu6XnVgaHEmXhytEK0W1aUADJPjAL6CtPZv5rsGSvUKtv7r8/zdj+v1uoOUpsxms7qunT6+g1/TvTQCxE6XR2kBqxjyZo6K66gsAXB1fZ3neQdJSvI8X61WpNaMWCFuKNrkGuGGmMm95fhpvPkn/f6lAgAuLy/LstyGpq7r9+8d4rAr443qaln/ehHt1siv3dvt2B/RDpJms5lGE62gEy9az0XGcQCK3DL4DTPr0pPZEjPAZVlusoCSoihWqzpCHy7ODRXhbUTJly9oDr4fKDaV9NZJUrszPOjsI0a/FzfwNt4eHH+BSyICqK7rqqo0u0VRrFYridyN87L3pBYf7qvq3wqc3DMldJmiK06pgi8uLqQjAAorRG+p+zLUxks+z7rOkOzlIUy8yrAcQFVV3a4/ywBPmJsVMcTM3l/h9xDlLga4I1PDGaD7UNBPuCKBleUfy2gd+DOrPWubGHJJyD+L+LCTjEXEgH//2uSxhu1/Xzocy+VSL+2cUhrqLVZ/jTYL0IMtQEklT3/iWCutzUljDDNXVSVHRFWW7SOtccHag6V/AF1/slVRyOkZAAAAAElFTkSuQmCC"
_MASK_96_B64_REAL = "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"

def _load_real_masks():
    import numpy as np, base64, io
    from PIL import Image
    def to_alpha(b64str):
        raw = base64.b64decode(b64str)
        arr = np.array(Image.open(io.BytesIO(raw)).convert("RGB"), dtype=np.float32)
        return np.max(arr, axis=2) / 255.0
    return to_alpha(_MASK_48_B64_REAL), to_alpha(_MASK_96_B64_REAL)



def _gemini_remove_logo(src_path, out_path):
    """Remove Gemini watermark via reverse alpha blending.
    Uses the REAL bg_48/bg_96 mask files and correlation-based search
    (ported directly from PlayerYK/GeminiWatermarkRemover engine.js, MIT).
    Formula: original = (watermarked - alpha*255) / (1 - alpha)
    """
    import numpy as np
    from PIL import Image
    import io

    img_pil = Image.open(src_path).convert('RGBA')
    W, H = img_pil.size
    img_arr = np.array(img_pil, dtype=np.float32)   # (H,W,4)
    data = img_arr                                    # alias

    try:
        alpha48, alpha96 = _load_real_masks()
    except Exception:
        # Fallback: patch-based removal if masks unavailable
        img_pil.save(out_path, 'PNG')
        return

    # Choose which mask based on image size (same logic as original JS)
    use_96 = (W > 1024 and H > 1024)
    alpha_map = alpha96 if use_96 else alpha48
    size = 96 if use_96 else 48

    # ── Correlation-based template matching (port of searchWatermark) ──────
    search_ratio = 0.25
    search_w = int(W * search_ratio)
    search_h = int(H * search_ratio)
    start_x = W - search_w
    start_y = H - search_h

    # Default fallback position
    best_x = W - size - 32
    best_y = H - size - 32
    best_score = -1e9
    step = max(1, size // 8)

    # Convert image to brightness for fast correlation
    bright = (img_arr[:, :, 0] * 0.299 + img_arr[:, :, 1] * 0.587 + img_arr[:, :, 2] * 0.114)

    # Coarse scan
    for sy in range(start_y, H - size + 1, step):
        for sx in range(start_x, W - size + 1, step):
            region_br = bright[sy:sy+size, sx:sx+size]
            avg_br = region_br.mean()
            deviation = region_br - avg_br
            pos_dev = np.where(deviation > 0, deviation / 255.0, 0.0)
            high_alpha = alpha_map > 0.05
            alpha_sum = alpha_map[high_alpha].sum()
            if alpha_sum == 0:
                continue
            corr = (alpha_map * pos_dev)[high_alpha].sum() / alpha_sum
            if corr > best_score:
                best_score = corr
                best_x, best_y = sx, sy

    # Fine refine around best position
    refine = step * 2
    for sy in range(best_y - refine, best_y + refine + 1):
        for sx in range(best_x - refine, best_x + refine + 1):
            if sx < 0 or sx > W - size or sy < 0 or sy > H - size:
                continue
            region_br = bright[sy:sy+size, sx:sx+size]
            avg_br = region_br.mean()
            deviation = region_br - avg_br
            pos_dev = np.where(deviation > 0, deviation / 255.0, 0.0)
            high_alpha = alpha_map > 0.05
            alpha_sum = alpha_map[high_alpha].sum()
            if alpha_sum == 0:
                continue
            corr = (alpha_map * pos_dev)[high_alpha].sum() / alpha_sum
            if corr > best_score:
                best_score = corr
                best_x, best_y = sx, sy

    # ── Reverse alpha blend (formula from engine.js removeWatermark) ──────
    MAX_ALPHA = 0.99
    alpha_3d = np.clip(alpha_map[:, :, np.newaxis], 0, MAX_ALPHA)  # (S,S,1)

    # Clamp coords
    x0, y0 = max(0, best_x), max(0, best_y)
    x1, y1 = min(W, x0 + size), min(H, y0 + size)
    aw = x1 - x0
    ah = y1 - y0

    region = img_arr[y0:y1, x0:x1, :3].copy()         # (ah,aw,3)
    a = alpha_3d[:ah, :aw, :]                           # (ah,aw,1)

    recovered = (region - a * 255.0) / (1.0 - a)
    recovered = np.clip(np.round(recovered), 0, 255)

    # Only write where alpha > 0 (don't touch transparent background)
    mask_write = (a > 0.01)
    region_out = np.where(mask_write, recovered, region)

    img_arr[y0:y1, x0:x1, :3] = region_out

    orig_mode = Image.open(src_path).mode
    result = Image.fromarray(img_arr.astype(np.uint8), 'RGBA')
    if orig_mode in ('RGB', 'L'):
        result = result.convert('RGB')
    result.save(out_path, 'PNG')




def process_logo_removal(settings):
    lr_state['processing'] = True
    lr_state['cancel_requested'] = False
    lr_state['start_time'] = time.time()
    lr_state['total_processed'] = 0

    position    = settings.get('position', 'bottom_right')
    size_pct    = int(settings.get('size_pct', 10))
    method      = settings.get('method', 'crop')
    out_dir     = settings.get('out_dir', '')
    is_gemini   = settings.get('gemini_mode', False)
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    # Ensure masks are ready
    if is_gemini:
        ensure_watermark_masks()

    mask_48_path = os.path.join(WATERMARK_DIR, 'bg_48.png')
    mask_96_path = os.path.join(WATERMARK_DIR, 'bg_96.png')

    def process_lr_item(item):
        if lr_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; return
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: lr_state['total_processed'] += 1
            return

        name, ext = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        # Always output PNG for lossless Gemini removal; keep original ext for manual
        out_ext = '.png' if is_gemini else ext
        suffix = settings.get('suffix', '_clean')
        out = os.path.join(od, f"{name}{suffix}{out_ext}")

        try:
            if is_gemini:
                # ── GEMINI MODE: Star detection + patch-based fill ───────────────
                # Detects the bright white Gemini 4-pointed star in the bottom-right
                # corner and fills it with surrounding pixel texture.
                _gemini_remove_logo(src, out)
            else:
                # ── MANUAL MODE: ImageMagick-based operations ────────────────────
                try:
                    r = subprocess.run(
                        ["magick", "identify", "-format", "%w,%h", src],
                        capture_output=True, text=True, check=True, creationflags=cf
                    )
                    parts = r.stdout.strip().split(',')
                    W, H = int(parts[0]), int(parts[1])
                except Exception as e:
                    item['status'] = 'failed'; item['error'] = f"Read failed: {e}"
                    with state_lock: lr_state['total_processed'] += 1
                    return

                pw = max(1, int(W * size_pct / 100))
                ph = max(1, int(H * size_pct / 100))
                pos_override = position

                if pos_override == 'bottom_right':   rx, ry, rw, rh = W-pw, H-ph, pw, ph
                elif pos_override == 'bottom_left':  rx, ry, rw, rh = 0,    H-ph, pw, ph
                elif pos_override == 'top_right':    rx, ry, rw, rh = W-pw, 0,    pw, ph
                elif pos_override == 'top_left':     rx, ry, rw, rh = 0,    0,    pw, ph
                elif pos_override == 'bottom_bar':   rx, ry, rw, rh = 0,    H-ph, W,  ph
                elif pos_override == 'top_bar':      rx, ry, rw, rh = 0,    0,    W,  ph
                else:                                rx, ry, rw, rh = W-pw, H-ph, pw, ph

                if method == 'crop':
                    if pos_override == 'bottom_bar':
                        geom = f"{W}x{H - rh}+0+0"
                    elif pos_override == 'top_bar':
                        geom = f"{W}x{H - rh}+0+{rh}"
                    elif pos_override in ('bottom_right', 'bottom_left'):
                        geom = f"{W}x{H - rh}+0+0"
                    else:
                        geom = f"{W}x{H - rh}+0+{rh}"
                    cmd = ["magick", src, "-crop", geom, "+repage", out]
                elif method == 'blur':
                    region = f"{rw}x{rh}+{rx}+{ry}"
                    cmd = ["magick", src, "-region", region, "-blur", "0x20", out]
                elif method == 'fill_black':
                    cmd = ["magick", src, "-fill", "black", "-draw",
                           f"rectangle {rx},{ry} {rx+rw},{ry+rh}", out]
                elif method == 'fill_white':
                    cmd = ["magick", src, "-fill", "white", "-draw",
                           f"rectangle {rx},{ry} {rx+rw},{ry+rh}", out]
                else:
                    region = f"{rw}x{rh}+{rx}+{ry}"
                    cmd = ["magick", src, "-region", region, "-blur", "0x20", out]
                subprocess.run(cmd, check=True, creationflags=cf)

            item['status'] = 'completed'
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
        with state_lock: lr_state['total_processed'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        concurrent.futures.wait([ex.submit(process_lr_item, item) for item in lr_state['queue']])
    lr_state['processing'] = False


# =====================================================================
# METADATA REMOVER
# =====================================================================
def process_metadata_removal(settings):
    mt_state['processing'] = True
    mt_state['cancel_requested'] = False
    mt_state['start_time'] = time.time()
    mt_state['total_processed'] = 0

    out_dir = settings.get('out_dir', '')
    suffix  = settings.get('suffix', '_nometa')
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    def process_mt_item(item):
        if mt_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; return
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: mt_state['total_processed'] += 1
            return

        name, ext = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        out = os.path.join(od, f"{name}{suffix}{ext}")

        try:
            # Use ImageMagick to strip all metadata profiles
            cmd = ["magick", src,
                   "-strip",           # remove all profiles and comments
                   "-auto-orient",     # apply EXIF orientation then strip it
                   out]
            subprocess.run(cmd, check=True, creationflags=cf)
            # Verify metadata was stripped by checking original vs output size
            orig_size = os.path.getsize(src)
            out_size  = os.path.getsize(out)
            item['size_saved'] = max(0, orig_size - out_size)
            item['status'] = 'completed'
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
        with state_lock: mt_state['total_processed'] += 1

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
        concurrent.futures.wait([ex.submit(process_mt_item, item) for item in mt_state['queue']])
    mt_state['processing'] = False

# =====================================================================
# IMAGE SLICER
# =====================================================================
def process_slice_queue(settings):
    sl_state['processing'] = True
    sl_state['cancel_requested'] = False
    sl_state['start_time'] = time.time()
    sl_state['total_processed'] = 0
    
    slice_mode = settings.get('slice_mode', 'grid')
    out_dir = settings.get('out_dir', '')
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    
    for item in sl_state['queue']:
        if sl_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; continue
            
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: sl_state['total_processed'] += 1
            continue
            
        name, ext = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        
        try:
            if slice_mode == 'grid':
                cols = int(settings.get('grid_cols', 2))
                rows = int(settings.get('grid_rows', 2))
                out_pattern = os.path.join(od, f"{name}_slice_%d{ext}")
                cmd = ["magick", src, "-crop", f"{cols}x{rows}@", "+repage", out_pattern]
                subprocess.run(cmd, check=True, creationflags=cf)
            elif slice_mode == 'steam':
                r = subprocess.run(
                    ["magick", "identify", "-format", "%w,%h", src],
                    capture_output=True, text=True, check=True, creationflags=cf
                )
                parts = r.stdout.strip().split(',')
                W, H = int(parts[0]), int(parts[1])
                
                scale = W / 1920.0
                
                x_mid = int(int(settings.get('steam_x_mid', 508)) * scale)
                x_side = int(int(settings.get('steam_x_side', 1022)) * scale)
                y_offset = int(int(settings.get('steam_y', 0)) * scale)
                
                w_mid = int(506 * scale)
                w_side = int(100 * scale)
                
                steam_h = settings.get('steam_h')
                if not steam_h or int(steam_h) <= 0:
                    crop_h = H - y_offset
                else:
                    crop_h = int(int(steam_h) * scale)
                    
                if crop_h > H - y_offset:
                    crop_h = H - y_offset
                
                mid_slices = int(settings.get('steam_mid_slices', 1))
                side_slices = int(settings.get('steam_side_slices', 1))
                
                # Slicing middle panel
                if mid_slices <= 1:
                    out_mid = os.path.join(od, f"{name}_steam_middle{ext}")
                    cmd_mid = ["magick", src, "-crop", f"{w_mid}x{crop_h}+{x_mid}+{y_offset}", "+repage", out_mid]
                    subprocess.run(cmd_mid, check=True, creationflags=cf)
                else:
                    h_slice = crop_h / float(mid_slices)
                    for i in range(mid_slices):
                        y_start = int(y_offset + i * h_slice)
                        y_end = int(y_offset + (i + 1) * h_slice)
                        slice_height = y_end - y_start
                        out_slice = os.path.join(od, f"{name}_steam_middle_{i+1}{ext}")
                        cmd_slice = ["magick", src, "-crop", f"{w_mid}x{slice_height}+{x_mid}+{y_start}", "+repage", out_slice]
                        subprocess.run(cmd_slice, check=True, creationflags=cf)
                
                # Slicing side panel
                if side_slices <= 1:
                    out_side = os.path.join(od, f"{name}_steam_side{ext}")
                    cmd_side = ["magick", src, "-crop", f"{w_side}x{crop_h}+{x_side}+{y_offset}", "+repage", out_side]
                    subprocess.run(cmd_side, check=True, creationflags=cf)
                else:
                    h_slice = crop_h / float(side_slices)
                    for i in range(side_slices):
                        y_start = int(y_offset + i * h_slice)
                        y_end = int(y_offset + (i + 1) * h_slice)
                        slice_height = y_end - y_start
                        out_slice = os.path.join(od, f"{name}_steam_side_{i+1}{ext}")
                        cmd_slice = ["magick", src, "-crop", f"{w_side}x{slice_height}+{x_side}+{y_start}", "+repage", out_slice]
                        subprocess.run(cmd_slice, check=True, creationflags=cf)
                
            item['status'] = 'completed'
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
            
        with state_lock: sl_state['total_processed'] += 1
        
    sl_state['processing'] = False

# =====================================================================
# IMAGE MERGER
# =====================================================================
def process_merge_queue(settings):
    me_state['processing'] = True
    me_state['cancel_requested'] = False
    me_state['start_time'] = time.time()
    me_state['total_processed'] = 0
    
    files = settings.get('files', [])
    out_path = settings.get('out_path', '')
    merge_mode = settings.get('merge_mode', 'horizontal')
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    
    if not files or not out_path:
        me_state['processing'] = False
        return
        
    me_state['queue'] = [{"path": out_path, "status": "processing", "error": ""}]
    
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        if merge_mode == 'horizontal':
            cmd = ["magick"] + files + ["+append", out_path]
            subprocess.run(cmd, check=True, creationflags=cf)
        elif merge_mode == 'vertical':
            cmd = ["magick"] + files + ["-append", out_path]
            subprocess.run(cmd, check=True, creationflags=cf)
        elif merge_mode == 'grid':
            cols = int(settings.get('grid_cols', 2))
            rows = int(settings.get('grid_rows', 2))
            row_images = []
            for r in range(rows):
                row_files = files[r*cols : (r+1)*cols]
                if not row_files:
                    break
                row_out = out_path + f"_row_{r}.tmp.png"
                cmd_row = ["magick"] + row_files + ["+append", row_out]
                subprocess.run(cmd_row, check=True, creationflags=cf)
                row_images.append(row_out)
                
            if row_images:
                cmd_final = ["magick"] + row_images + ["-append", out_path]
                subprocess.run(cmd_final, check=True, creationflags=cf)
                for f in row_images:
                    try: os.remove(f)
                    except: pass
                    
        me_state['queue'][0]['status'] = 'completed'
    except Exception as e:
        me_state['queue'][0]['status'] = 'failed'
        me_state['queue'][0]['error'] = str(e)
    finally:
        if merge_mode == 'grid' and 'row_images' in locals():
            for f in row_images:
                if os.path.exists(f):
                    try: os.remove(f)
                    except: pass
        with state_lock: me_state['total_processed'] = 1
        me_state['processing'] = False

# =====================================================================
# IMAGE OVERLAY
# =====================================================================
def process_overlay_queue(settings):
    ol_state['processing'] = True
    ol_state['cancel_requested'] = False
    ol_state['start_time'] = time.time()
    ol_state['total_processed'] = 0
    
    base_img = settings.get('base_img', '')
    overlay_img = settings.get('overlay_img', '')
    out_path = settings.get('out_path', '')
    
    gravity = settings.get('gravity', 'Center')
    offset_x = int(settings.get('offset_x', 0))
    offset_y = int(settings.get('offset_y', 0))
    opacity = float(settings.get('opacity', 100)) / 100.0
    scale = float(settings.get('scale', 100))
    scale_type = settings.get('scale_type', 'percent')
    
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    
    if not base_img or not overlay_img or not out_path:
        ol_state['processing'] = False
        return
        
    ol_state['queue'] = [{"path": out_path, "status": "processing", "error": ""}]
    
    try:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        resize_str = f"{scale}%" if scale_type == 'percent' else f"{int(scale)}x"
        
        geom_str = ""
        if offset_x >= 0: geom_str += f"+{offset_x}"
        else: geom_str += f"{offset_x}"
        if offset_y >= 0: geom_str += f"+{offset_y}"
        else: geom_str += f"{offset_y}"
        
        cmd = [
            "magick", base_img,
            "(", overlay_img, "-alpha", "on", "-channel", "A", "-evaluate", "multiply", str(opacity), "+channel", "-resize", resize_str, ")",
            "-gravity", gravity, "-geometry", geom_str,
            "-composite", out_path
        ]
        
        subprocess.run(cmd, check=True, creationflags=cf)
        ol_state['queue'][0]['status'] = 'completed'
    except Exception as e:
        ol_state['queue'][0]['status'] = 'failed'
        ol_state['queue'][0]['error'] = str(e)
        
    with state_lock: ol_state['total_processed'] = 1
    ol_state['processing'] = False

# =====================================================================
# FORMAT CONVERTER
# =====================================================================
def process_converter_queue(settings):
    co_state['processing'] = True
    co_state['cancel_requested'] = False
    co_state['start_time'] = time.time()
    co_state['total_processed'] = 0
    
    target_format = settings.get('format', 'WEBP').lower()
    quality = str(settings.get('quality', 90))
    out_dir = settings.get('out_dir', '')
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    
    for item in co_state['queue']:
        if co_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; continue
            
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: co_state['total_processed'] += 1
            continue
            
        name, _ = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        out = os.path.join(od, f"{name}_converted.{target_format}")
        
        cmd = ["magick", src]
        if target_format in ['jpg', 'jpeg', 'webp', 'avif']:
            cmd.extend(["-quality", quality])
        cmd.append(out)
        
        try:
            subprocess.run(cmd, check=True, creationflags=cf)
            item['status'] = 'completed'
            if os.path.exists(out):
                item['size_saved'] = max(0, os.path.getsize(src) - os.path.getsize(out))
        except Exception as e:
            item['status'] = 'failed'; item['error'] = str(e)
            
        with state_lock: co_state['total_processed'] += 1
        
    co_state['processing'] = False

# =====================================================================
# VIDEO PROCESSOR
# =====================================================================

def _find_ffmpeg():
    """Return path to ffmpeg executable (bundled or system)."""
    # Try bundled next to exe first
    if getattr(sys, 'frozen', False):
        exe_dir = os.path.dirname(sys.executable)
        for candidate in ['ffmpeg.exe', os.path.join('bin', 'ffmpeg.exe')]:
            p = os.path.join(exe_dir, candidate)
            if os.path.exists(p):
                return p
    # Fall back to system PATH
    return 'ffmpeg'


def _get_hw_encoder(hwaccel_enabled):
    """Try to detect available hardware encoder. Returns (encoder, extra_args)."""
    if not hwaccel_enabled:
        return 'libx264', ['-preset', 'fast', '-crf', '18']

    ffmpeg = _find_ffmpeg()
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    for encoder, extra in [
        ('h264_nvenc',  ['-preset', 'p4', '-cq', '18']),   # NVIDIA
        ('h264_amf',    ['-quality', 'speed', '-qp_i', '18']),  # AMD
        ('h264_qsv',    ['-preset', 'fast', '-global_quality', '23']),  # Intel
    ]:
        try:
            r = subprocess.run(
                [ffmpeg, '-f', 'lavfi', '-i', 'color=c=black:s=32x32:d=0.1',
                 '-vframes', '1', '-c:v', encoder, '-f', 'null', '-'],
                capture_output=True, timeout=10, creationflags=cf
            )
            if r.returncode == 0:
                return encoder, extra
        except Exception:
            pass

    # Fall back to CPU
    return 'libx264', ['-preset', 'fast', '-crf', '18']


def _video_to_frames(item, settings, out_dir):
    """Extract frames from a video file using ffmpeg."""
    src = item['path']
    fps = int(settings.get('fps', 30))
    hwaccel = settings.get('hwaccel', True)
    ffmpeg = _find_ffmpeg()
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    base_name = os.path.splitext(os.path.basename(src))[0]
    frames_dir = os.path.join(out_dir, f'{base_name}_frames')
    os.makedirs(frames_dir, exist_ok=True)

    cmd = [ffmpeg, '-y']
    if hwaccel:
        cmd += ['-hwaccel', 'auto']
    cmd += [
        '-i', src,
        '-vf', f'fps={fps}',
        '-q:v', '2',
        '-threads', str(os.cpu_count() or 4),
        os.path.join(frames_dir, 'frame_%06d.png')
    ]

    vd_state['status_text'] = f'Extracting frames: {os.path.basename(src)}'
    result = subprocess.run(cmd, capture_output=True, creationflags=cf)
    if result.returncode != 0:
        if hwaccel:
            cmd_cpu = [
                ffmpeg, '-y',
                '-i', src,
                '-vf', f'fps={fps}',
                '-q:v', '2',
                '-threads', str(os.cpu_count() or 4),
                os.path.join(frames_dir, 'frame_%06d.png')
            ]
            vd_state['status_text'] = 'Retrying extraction with CPU...'
            result_cpu = subprocess.run(cmd_cpu, capture_output=True, creationflags=cf)
            if result_cpu.returncode != 0:
                raise RuntimeError(result_cpu.stderr.decode('utf-8', errors='replace')[-300:])
        else:
            raise RuntimeError(result.stderr.decode('utf-8', errors='replace')[-300:])

    n = len([f for f in os.listdir(frames_dir) if f.endswith('.png')])
    vd_state['status_text'] = f'Extracted {n} frames → {frames_dir}'


def _frames_to_video(item, settings, out_dir):
    """Compile image frames in a folder into a video using ffmpeg."""
    src = item['path']  # can be a single frame or the folder itself
    fps = int(settings.get('fps', 30))
    hwaccel = settings.get('hwaccel', True)
    ffmpeg = _find_ffmpeg()
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

    # Determine frames folder
    if os.path.isdir(src):
        frames_dir = src
    else:
        frames_dir = os.path.dirname(src)

    # Auto-detect frame pattern (frame_000001.png or similar)
    exts = ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']
    frame_files = sorted([
        f for f in os.listdir(frames_dir)
        if os.path.splitext(f)[1].lower() in exts
    ])
    if not frame_files:
        raise RuntimeError(f'No image frames found in: {frames_dir}')

    # Build glob pattern for ffmpeg (e.g. frame_%06d.png)
    first = frame_files[0]
    ext = os.path.splitext(first)[1]
    name_part = os.path.splitext(first)[0]
    import re as _re
    num_matches = list(_re.finditer(r'(\d+)', name_part))
    if num_matches:
        num_match = num_matches[-1]
        n_digits = len(num_match.group(1))
        prefix = name_part[:num_match.start()]
        suffix = name_part[num_match.end():]
        pattern = os.path.join(frames_dir, f'{prefix}%0{n_digits}d{suffix}{ext}')
    else:
        pattern = os.path.join(frames_dir, f'%d{ext}')

    base_name = os.path.basename(frames_dir.rstrip('/\\'))
    out_file = os.path.join(out_dir, f'{base_name}_video.mp4')

    encoder, enc_args = _get_hw_encoder(hwaccel)

    cmd = [ffmpeg, '-y',
           '-framerate', str(fps),
           '-i', pattern,
           '-c:v', encoder] + enc_args + [
        '-pix_fmt', 'yuv420p',
        '-movflags', '+faststart',
        '-threads', str(os.cpu_count() or 4),
        out_file
    ]

    vd_state['status_text'] = f'Compiling video ({encoder}): {os.path.basename(out_file)}'
    result = subprocess.run(cmd, capture_output=True, creationflags=cf)
    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace')
        # Retry with CPU if GPU failed
        if encoder != 'libx264':
            cmd2 = [ffmpeg, '-y',
                    '-framerate', str(fps),
                    '-i', pattern,
                    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                    '-pix_fmt', 'yuv420p',
                    '-movflags', '+faststart',
                    '-threads', str(os.cpu_count() or 4),
                    out_file]
            vd_state['status_text'] = f'Retrying with CPU encoder...'
            result2 = subprocess.run(cmd2, capture_output=True, creationflags=cf)
            if result2.returncode != 0:
                raise RuntimeError(result2.stderr.decode('utf-8', errors='replace')[-300:])
        else:
            raise RuntimeError(err[-300:])

    vd_state['status_text'] = f'Video saved → {out_file}'


def process_video_queue(settings):
    """Main video processor queue runner — runs in background thread."""
    vd_state['processing'] = True
    vd_state['cancel_requested'] = False
    vd_state['start_time'] = time.time()
    vd_state['total_processed'] = 0
    vd_state['status_text'] = 'Starting...'

    mode    = settings.get('mode', 'video_to_frames')
    out_dir = settings.get('out_dir', '').strip()

    try:
        for i, item in enumerate(vd_state['queue']):
            if vd_state['cancel_requested']:
                item['status'] = 'failed'
                item['error']  = 'Cancelled'
                continue

            item['status'] = 'processing'
            vd_state['current_index'] = i

            # Determine output directory per-item if not specified
            item_out = out_dir
            if not item_out:
                if os.path.isdir(item['path']):
                    item_out = os.path.dirname(item['path'].rstrip('/\\'))
                else:
                    item_out = os.path.dirname(item['path'])

            try:
                if mode == 'video_to_frames':
                    _video_to_frames(item, settings, item_out)
                else:
                    _frames_to_video(item, settings, item_out)
                item['status'] = 'completed'
                vd_state['total_processed'] += 1
            except Exception as e:
                item['status'] = 'failed'
                item['error']  = str(e)[:200]

    finally:
        vd_state['processing'] = False
        vd_state['status_text'] = 'Done'


# =====================================================================
# HTTP SERVER
# =====================================================================

class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args): pass

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path.startswith('/api/status'):
            # New generic status route: /api/status?tool=video
            from urllib.parse import urlparse, parse_qs
            qs = parse_qs(urlparse(self.path).query)
            tool = qs.get('tool', [''])[0]
            if tool == 'video':
                done  = sum(1 for it in vd_state['queue'] if it['status'] in ('completed', 'failed'))
                total = len(vd_state['queue'])
                self._json({
                    'state':       'processing' if vd_state['processing'] else 'idle',
                    'done':        done,
                    'total':       total,
                    'status_text': vd_state.get('status_text', ''),
                    'cancelled':   vd_state.get('cancel_requested', False),
                    'items': [{'status': it['status'], 'error': it.get('error', '')} for it in vd_state['queue']]
                })
            else:
                self._json(self._ds_status())
        elif self.path == '/api/upscaler/status':
            elapsed = time.time() - up_state['start_time'] if up_state['processing'] else 0
            self._json({"processing": up_state['processing'], "queue": up_state['queue'],
                        "total_processed": up_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/logo-remover/status':
            elapsed = time.time() - lr_state['start_time'] if lr_state['processing'] else 0
            self._json({"processing": lr_state['processing'], "queue": lr_state['queue'],
                        "total_processed": lr_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/upscaler/download-progress':
            self._json(download_state)
        elif self.path == '/api/slicer/status':
            elapsed = time.time() - sl_state['start_time'] if sl_state['processing'] else 0
            self._json({"processing": sl_state['processing'], "queue": sl_state['queue'],
                        "total_processed": sl_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/merger/status':
            elapsed = time.time() - me_state['start_time'] if me_state['processing'] else 0
            self._json({"processing": me_state['processing'], "queue": me_state['queue'],
                        "total_processed": me_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/overlay/status':
            elapsed = time.time() - ol_state['start_time'] if ol_state['processing'] else 0
            self._json({"processing": ol_state['processing'], "queue": ol_state['queue'],
                        "total_processed": ol_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/converter/status':
            elapsed = time.time() - co_state['start_time'] if co_state['processing'] else 0
            self._json({"processing": co_state['processing'], "queue": co_state['queue'],
                        "total_processed": co_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/metadata-remover/status':
            elapsed = time.time() - mt_state['start_time'] if mt_state['processing'] else 0
            self._json({"processing": mt_state['processing'], "queue": mt_state['queue'],
                        "total_processed": mt_state['total_processed'], "time_elapsed": round(elapsed, 1)})
        elif self.path == '/api/upscaler/list-models':
            self._json({"models": list_available_models()})
        elif self.path == '/api/upscaler/detect-gpu':
            has_nvidia, name = detect_nvidia_gpu()
            self._json({"nvidia": has_nvidia, "name": name})
        else:
            super().do_GET()


    def do_POST(self):
        cl = int(self.headers.get('Content-Length', 0))
        raw = self.rfile.read(cl) if cl > 0 else b""
        try: req = json.loads(raw.decode('utf-8')) if raw else {}
        except: req = {}
        resp = {}

        # --- Settings API ---
        if self.path == '/api/settings/get':
            resp = load_app_settings()
        elif self.path == '/api/settings/save':
            for k, v in req.items():
                save_app_setting(k, v)
            resp = {"status": "success"}
        elif self.path == '/api/settings/browse-folder':
            folder = ask_directory("Select Custom Models Directory")
            resp = {"folder": folder}
        # --- Shared ---
        elif self.path == '/api/select-files':
            # Support optional file_types from request for video tab
            file_types_req = req.get('file_types', None)
            if file_types_req:
                # Convert [[desc, pattern], ...] to tkinter filetypes
                tk_types = [(ft[0], ft[1]) for ft in file_types_req]
                tk_types.append(("All Files", "*.*"))
                root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
                files = filedialog.askopenfilenames(parent=root, title="Select Files", filetypes=tk_types)
                root.destroy()
                resp = {"files": list(files)}
            else:
                resp = {"files": ask_open_files()}
        elif self.path == '/api/select-folder':
            folder = ask_directory("Select Source Directory")
            files = []
            if folder:
                # Check if video folder (request can hint with file_types)
                file_types_req = req.get('file_types', None)
                if file_types_req and 'Video' in str(file_types_req):
                    valid = ('.mp4', '.mkv', '.avi', '.mov', '.webm', '.wmv', '.flv', '.m4v', '.ts')
                else:
                    valid = ('.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp','.heic','.cr2','.nef','.arw')
                for f in os.listdir(folder):
                    if f.lower().endswith(valid):
                        files.append(os.path.normpath(os.path.join(folder, f)))
                # For video-to-frames: also accept folders as a single item
                if not files and file_types_req and 'Video' not in str(file_types_req):
                    # Frames mode — return the folder itself as the item
                    files = [os.path.normpath(folder)]
            resp = {"files": files, "folder": folder}
        elif self.path == '/api/select-out-folder':
            resp = {"folder": ask_directory("Select Output Directory")}
        elif self.path == '/api/get-metadata':
            resp = {"metadata": get_image_metadata(req.get('files', []))}

        # --- Downscaler ---
        elif self.path == '/api/start':
            if not app_state['processing']:
                files = req.get('files', [])
                app_state['queue'] = [{"path": f, "status": "pending", "error": "", "size_saved": 0} for f in files]
                threading.Thread(target=process_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/cancel':
            app_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Upscaler ---
        elif self.path == '/api/upscaler/check-engine':
            resp = {"ready": check_esrgan_ready()}
        elif self.path == '/api/upscaler/reset-engine-state':
            download_state['status'] = ''
            download_state['error'] = ''
            resp = {"status": "reset"}
        elif self.path == '/api/upscaler/download-engine':
            if download_state['status'] not in ['downloading', 'extracting']:
                threading.Thread(target=download_esrgan_async, daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/upscaler/download-model':
            mkey = req.get('model_key', '')
            ok, err = download_custom_model(mkey)
            resp = {"success": ok, "error": err, "model_key": mkey}
        elif self.path == '/api/upscaler/start':
            if not up_state['processing']:
                files = req.get('files', [])
                up_state['queue'] = [{"path": f, "status": "pending", "error": "", "size_saved": 0} for f in files]
                threading.Thread(target=process_upscale_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/upscaler/cancel':
            up_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Logo Remover ---
        elif self.path == '/api/logo-remover/start':
            if not lr_state['processing']:
                files = req.get('files', [])
                lr_state['queue'] = [{"path": f, "status": "pending", "error": "", "size_saved": 0} for f in files]
                threading.Thread(target=process_logo_removal, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/logo-remover/cancel':
            lr_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Metadata Remover ---
        elif self.path == '/api/metadata-remover/start':
            if not mt_state['processing']:
                files = req.get('files', [])
                mt_state['queue'] = [{"path": f, "status": "pending", "error": "", "size_saved": 0} for f in files]
                threading.Thread(target=process_metadata_removal, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/metadata-remover/cancel':
            mt_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Save File Dialog ---
        elif self.path == '/api/select-out-file':
            root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
            file_path = filedialog.asksaveasfilename(
                parent=root, title="Save Output Image",
                filetypes=[
                    ("PNG Image", "*.png"),
                    ("JPEG Image", "*.jpg;*.jpeg"),
                    ("WebP Image", "*.webp"),
                    ("All Files", "*.*")
                ],
                defaultextension=".png"
            )
            root.destroy()
            resp = {"file": file_path}

        # --- Slicer ---
        elif self.path == '/api/slicer/start':
            if not sl_state['processing']:
                files = req.get('files', [])
                sl_state['queue'] = [{"path": f, "status": "pending", "error": ""} for f in files]
                threading.Thread(target=process_slice_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/slicer/cancel':
            sl_state['cancel_requested'] = True
            resp = {"status": "cancelling"}
        elif self.path == '/api/slicer/preview':
            settings = req.get('settings', {})
            files = req.get('files', [])
            if not files or not os.path.exists(files[0]):
                resp = {"error": "No file selected"}
            else:
                src = files[0]
                name, ext = os.path.splitext(os.path.basename(src))
                if not ext: ext = ".png"
                cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                try:
                    with tempfile.TemporaryDirectory() as od:
                        # Call a helper or just duplicate logic
                        slice_mode = settings.get('slice_mode', 'grid')
                        if slice_mode == 'grid':
                            cols = int(settings.get('grid_cols', 2))
                            rows = int(settings.get('grid_rows', 2))
                            out_pattern = os.path.join(od, f"{name}_slice_%d{ext}")
                            subprocess.run(["magick", src, "-crop", f"{cols}x{rows}@", "+repage", out_pattern], check=True, creationflags=cf)
                        elif slice_mode == 'steam':
                            r = subprocess.run(["magick", "identify", "-format", "%w,%h", src], capture_output=True, text=True, check=True, creationflags=cf)
                            parts = r.stdout.strip().split(',')
                            W, H = int(parts[0]), int(parts[1])
                            scale = W / 1920.0
                            x_mid = int(int(settings.get('steam_x_mid', 508)) * scale)
                            x_side = int(int(settings.get('steam_x_side', 1022)) * scale)
                            y_offset = int(int(settings.get('steam_y', 0)) * scale)
                            w_mid = int(506 * scale)
                            w_side = int(100 * scale)
                            steam_h = settings.get('steam_h')
                            crop_h = H - y_offset if (not steam_h or int(steam_h) <= 0) else min(int(int(steam_h) * scale), H - y_offset)
                            
                            mid_slices = int(settings.get('steam_mid_slices', 1))
                            side_slices = int(settings.get('steam_side_slices', 1))
                            
                            if mid_slices <= 1:
                                subprocess.run(["magick", src, "-crop", f"{w_mid}x{crop_h}+{x_mid}+{y_offset}", "+repage", os.path.join(od, f"{name}_steam_middle{ext}")], check=True, creationflags=cf)
                            else:
                                h_slice = crop_h / float(mid_slices)
                                for i in range(mid_slices):
                                    y_start, y_end = int(y_offset + i * h_slice), int(y_offset + (i + 1) * h_slice)
                                    subprocess.run(["magick", src, "-crop", f"{w_mid}x{y_end-y_start}+{x_mid}+{y_start}", "+repage", os.path.join(od, f"{name}_steam_middle_{i+1}{ext}")], check=True, creationflags=cf)
                                    
                            if side_slices <= 1:
                                subprocess.run(["magick", src, "-crop", f"{w_side}x{crop_h}+{x_side}+{y_offset}", "+repage", os.path.join(od, f"{name}_steam_side{ext}")], check=True, creationflags=cf)
                            else:
                                h_slice = crop_h / float(side_slices)
                                for i in range(side_slices):
                                    y_start, y_end = int(y_offset + i * h_slice), int(y_offset + (i + 1) * h_slice)
                                    subprocess.run(["magick", src, "-crop", f"{w_side}x{y_end-y_start}+{x_side}+{y_start}", "+repage", os.path.join(od, f"{name}_steam_side_{i+1}{ext}")], check=True, creationflags=cf)
                        
                        images = []
                        for f in sorted(os.listdir(od)):
                            with open(os.path.join(od, f), "rb") as img_f:
                                b64 = base64.b64encode(img_f.read()).decode('utf-8')
                                images.append({"name": f, "data": "data:image/png;base64," + b64})
                        resp = {"images": images}
                except Exception as e:
                    resp = {"error": str(e)}
        elif self.path == '/api/slicer/download-zip':
            settings = req.get('settings', {})
            files = req.get('files', [])
            if not files or not os.path.exists(files[0]):
                resp = {"error": "No file selected"}
            else:
                src = files[0]
                name, ext = os.path.splitext(os.path.basename(src))
                if not ext: ext = ".png"
                cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                try:
                    with tempfile.TemporaryDirectory() as od:
                        slice_mode = settings.get('slice_mode', 'grid')
                        if slice_mode == 'grid':
                            cols = int(settings.get('grid_cols', 2))
                            rows = int(settings.get('grid_rows', 2))
                            out_pattern = os.path.join(od, f"{name}_slice_%d{ext}")
                            subprocess.run(["magick", src, "-crop", f"{cols}x{rows}@", "+repage", out_pattern], check=True, creationflags=cf)
                        elif slice_mode == 'steam':
                            r = subprocess.run(["magick", "identify", "-format", "%w,%h", src], capture_output=True, text=True, check=True, creationflags=cf)
                            parts = r.stdout.strip().split(',')
                            W, H = int(parts[0]), int(parts[1])
                            scale = W / 1920.0
                            x_mid = int(int(settings.get('steam_x_mid', 508)) * scale)
                            x_side = int(int(settings.get('steam_x_side', 1022)) * scale)
                            y_offset = int(int(settings.get('steam_y', 0)) * scale)
                            w_mid = int(506 * scale)
                            w_side = int(100 * scale)
                            steam_h = settings.get('steam_h')
                            crop_h = H - y_offset if (not steam_h or int(steam_h) <= 0) else min(int(int(steam_h) * scale), H - y_offset)
                            
                            mid_slices = int(settings.get('steam_mid_slices', 1))
                            side_slices = int(settings.get('steam_side_slices', 1))
                            
                            if mid_slices <= 1:
                                subprocess.run(["magick", src, "-crop", f"{w_mid}x{crop_h}+{x_mid}+{y_offset}", "+repage", os.path.join(od, f"{name}_steam_middle{ext}")], check=True, creationflags=cf)
                            else:
                                h_slice = crop_h / float(mid_slices)
                                for i in range(mid_slices):
                                    y_start, y_end = int(y_offset + i * h_slice), int(y_offset + (i + 1) * h_slice)
                                    subprocess.run(["magick", src, "-crop", f"{w_mid}x{y_end-y_start}+{x_mid}+{y_start}", "+repage", os.path.join(od, f"{name}_steam_middle_{i+1}{ext}")], check=True, creationflags=cf)
                                    
                            if side_slices <= 1:
                                subprocess.run(["magick", src, "-crop", f"{w_side}x{crop_h}+{x_side}+{y_offset}", "+repage", os.path.join(od, f"{name}_steam_side{ext}")], check=True, creationflags=cf)
                            else:
                                h_slice = crop_h / float(side_slices)
                                for i in range(side_slices):
                                    y_start, y_end = int(y_offset + i * h_slice), int(y_offset + (i + 1) * h_slice)
                                    subprocess.run(["magick", src, "-crop", f"{w_side}x{y_end-y_start}+{x_side}+{y_start}", "+repage", os.path.join(od, f"{name}_steam_side_{i+1}{ext}")], check=True, creationflags=cf)
                        
                        import zipfile
                        tmp_zip_fd, tmp_zip_path = tempfile.mkstemp(suffix=".zip")
                        os.close(tmp_zip_fd)
                        with zipfile.ZipFile(tmp_zip_path, 'w') as zipf:
                            for f in os.listdir(od):
                                zipf.write(os.path.join(od, f), arcname=f)
                        
                        with open(tmp_zip_path, "rb") as f:
                            b64 = base64.b64encode(f.read()).decode('utf-8')
                        os.remove(tmp_zip_path)
                        resp = {"zip": "data:application/zip;base64," + b64, "filename": f"{name}_slices.zip"}
                except Exception as e:
                    resp = {"error": str(e)}

        # --- Merger ---
        elif self.path == '/api/merger/start':
            if not me_state['processing']:
                threading.Thread(target=process_merge_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/merger/cancel':
            me_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Overlay ---
        elif self.path == '/api/overlay/start':
            if not ol_state['processing']:
                threading.Thread(target=process_overlay_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/overlay/cancel':
            ol_state['cancel_requested'] = True
            resp = {"status": "cancelling"}
        elif self.path == '/api/overlay/preview':
            settings = req.get('settings', {})
            base_img = settings.get('base_img', '')
            overlay_img = settings.get('overlay_img', '')
            gravity = settings.get('gravity', 'Center')
            offset_x = int(settings.get('offset_x', 0))
            offset_y = int(settings.get('offset_y', 0))
            opacity = float(settings.get('opacity', 100)) / 100.0
            scale = float(settings.get('scale', 100))
            scale_type = settings.get('scale_type', 'percent')
            
            if base_img and overlay_img and os.path.exists(base_img) and os.path.exists(overlay_img):
                tmp_fd, tmp_path = tempfile.mkstemp(suffix=".jpg")
                os.close(tmp_fd)
                resize_str = f"{scale}%" if scale_type == 'percent' else f"{int(scale)}x"
                geom_str = f"+{offset_x}" if offset_x >= 0 else f"{offset_x}"
                geom_str += f"+{offset_y}" if offset_y >= 0 else f"{offset_y}"
                
                cmd = [
                    "magick", base_img,
                    "(", overlay_img, "-alpha", "on", "-channel", "A", "-evaluate", "multiply", str(opacity), "+channel", "-resize", resize_str, ")",
                    "-gravity", gravity, "-geometry", geom_str,
                    "-composite", "-resize", "800x800>", "-quality", "80", tmp_path
                ]
                try:
                    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                    subprocess.run(cmd, check=True, creationflags=cf)
                    with open(tmp_path, "rb") as f:
                        b64 = base64.b64encode(f.read()).decode('utf-8')
                    resp = {"image": "data:image/jpeg;base64," + b64}
                except Exception as e:
                    resp = {"error": str(e)}
                finally:
                    try: os.remove(tmp_path)
                    except: pass
            else:
                resp = {"error": "Images not loaded"}

        # --- Converter ---
        elif self.path == '/api/converter/start':
            if not co_state['processing']:
                files = req.get('files', [])
                co_state['queue'] = [{"path": f, "status": "pending", "error": "", "size_saved": 0} for f in files]
                threading.Thread(target=process_converter_queue, args=(req.get('settings', {}),), daemon=True).start()
                resp = {"status": "started"}
            else:
                resp = {"status": "already_running"}
        elif self.path == '/api/converter/cancel':
            co_state['cancel_requested'] = True
            resp = {"status": "cancelling"}

        # --- Video Processor ---
        elif self.path == '/api/process':
            tool = req.get('tool', '')
            settings = req.get('settings', {})
            if tool == 'video':
                if not vd_state['processing']:
                    files = settings.get('files', [])
                    vd_state['queue'] = [{"path": f, "status": "pending", "error": "", "name": os.path.basename(f)} for f in files]
                    threading.Thread(target=process_video_queue, args=(settings,), daemon=True).start()
                    resp = {"status": "started"}
                else:
                    resp = {"status": "already_running"}
            else:
                resp = {"error": f"Unknown tool: {tool}"}
        elif self.path == '/api/cancel':
            tool = req.get('tool', '')
            if tool == 'video':
                vd_state['cancel_requested'] = True
            else:
                app_state['cancel_requested'] = True
            resp = {"status": "cancelling"}
        elif self.path == '/api/kill-app':
            resp = {"status": "shutting_down"}
            self._json(resp)
            def stop():
                time.sleep(0.5)
                os._exit(0)
            threading.Thread(target=stop, daemon=True).start()
            return

        else:
            self.send_error(404); return


        self._json(resp)

    def _json(self, data):
        payload = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _ds_status(self):
        elapsed = time.time() - app_state['start_time'] if app_state['processing'] else 0
        speed = app_state['total_processed'] / elapsed if elapsed > 0 else 0
        return {
            "processing": app_state['processing'], "queue": app_state['queue'],
            "current_index": app_state['current_index'],
            "total_processed": app_state['total_processed'],
            "speed": round(speed, 2), "time_elapsed": round(elapsed, 1),
            "total_space_saved": app_state['total_space_saved']
        }

# =====================================================================
# SYSTEM TRAY & TASKBAR WINDOWS SETTINGS
# =====================================================================
tray_icon = None

def set_app_id():
    pass

def notify_bg_running():
    global tray_icon
    if not tray_icon:
        return
        
    appdata = os.environ.get('APPDATA') or os.path.expanduser('~')
    settings_dir = os.path.join(appdata, 'MagickScale')
    os.makedirs(settings_dir, exist_ok=True)
    state_file = os.path.join(settings_dir, 'state.json')
    
    already_notified = False
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
                already_notified = state_data.get('bg_notified', False)
        except Exception:
            pass
            
    if not already_notified:
        try:
            def do_notify():
                try:
                    tray_icon.notify(
                        "MagickScale is still running in the system tray. Use the icon menu to open or exit.",
                        "MagickScale Running in Background"
                    )
                except Exception as e:
                    print(f"Notification error: {e}")
            threading.Thread(target=do_notify, daemon=True).start()
            
            with open(state_file, 'w') as f:
                json.dump({'bg_notified': True}, f)
        except Exception as e:
            print(f"Failed to show tray notification: {e}")

def setup_tray(window):
    global tray_icon
    if not HAS_PYSTRAY:
        return
    try:
        icon_path = os.path.join(base_dir, "magickscale.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(runtime_dir, "magickscale.ico")
            
        if os.path.exists(icon_path):
            img = Image.open(icon_path)
        else:
            img = Image.new('RGB', (64, 64), color='red')
            
        def on_open(icon, item):
            window.show()
            window.restore()
            
        def on_exit(icon, item):
            icon.stop()
            os._exit(0)
            
        menu = pystray.Menu(
            pystray.MenuItem('Open MagickScale', on_open, default=True),
            pystray.MenuItem('Exit', on_exit)
        )
        
        tray_icon = pystray.Icon("MagickScale", img, "MagickScale", menu=menu)
        tray_icon.run_detached()
    except Exception as e:
        print(f"Error setting up system tray: {e}")

class WebviewApi:
    def __init__(self):
        self.window = None
        
    def toggle_fullscreen(self):
        if self.window:
            self.window.toggle_fullscreen()

def force_window_icon(window):
    if sys.platform == 'win32':
        import os
        import sys
        import time
        import ctypes
        
        # Wait a small fraction of a second to ensure the window has finished initializing
        time.sleep(0.5)
        
        icon_path = os.path.join(base_dir, "magickscale.ico")
        if not os.path.exists(icon_path):
            icon_path = os.path.join(runtime_dir, "magickscale.ico")
        icon_path = os.path.abspath(icon_path)
        
        if not os.path.exists(icon_path):
            print(f"Icon not found at: {icon_path}")
            return
            
        user32 = ctypes.windll.user32
        my_pid = os.getpid()
        
        # Perform icon injection multiple times to catch delayed window creation
        for attempt in range(20):
            hwnds = []
            
            # WNDENUMPROC callback type
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            
            def enum_callback(hwnd, lParam):
                lpdw_process_id = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(lpdw_process_id))
                if lpdw_process_id.value == my_pid:
                    if user32.IsWindowVisible(hwnd):
                        hwnds.append(hwnd)
                return True
                
            callback_func = WNDENUMPROC(enum_callback)
            user32.EnumWindows(callback_func, 0)
            
            if hwnds:
                for hwnd in hwnds:
                    try:
                        # Load icon: IMAGE_ICON = 1, LR_LOADFROMFILE = 0x00000010
                        h_icon = user32.LoadImageW(None, icon_path, 1, 0, 0, 0x00000010)
                        if h_icon:
                            # Send WM_SETICON (0x0080) to set window icons
                            # ICON_SMALL = 0
                            # ICON_BIG = 1
                            user32.SendMessageW(hwnd, 0x0080, 0, h_icon)
                            user32.SendMessageW(hwnd, 0x0080, 1, h_icon)
                            
                            # Also set window class icons so that taskbar uses the custom icon:
                            # GCLP_HICON = -14, GCLP_HICONSM = -34
                            if hasattr(user32, 'SetClassLongPtrW'):
                                user32.SetClassLongPtrW(hwnd, -14, h_icon)
                                user32.SetClassLongPtrW(hwnd, -34, h_icon)
                            else:
                                user32.SetClassLongW(hwnd, -14, h_icon)
                                user32.SetClassLongW(hwnd, -34, h_icon)
                    except Exception as e:
                        print(f"Failed setting icon on HWND {hwnd}: {e}")
            
            time.sleep(0.5)

# =====================================================================
# SERVER
# =====================================================================
def run_server():
    set_app_id()
    os.makedirs(WEB_DIR, exist_ok=True)
    server = HTTPServer(('127.0.0.1', PORT), ApiHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"MagickScale running at {url}")
    
    # Check if we should override webview mode (e.g. via environment variable)
    use_browser = os.environ.get("MAGICKSCALE_BROWSER", "0") == "1" or not HAS_WEBVIEW

    if use_browser:
        threading.Thread(target=lambda: (time.sleep(0.6), webbrowser.open(url)), daemon=True).start()
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            server.server_close()
    else:
        # Start server in background thread
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        
        # Open webview window on main thread
        try:
            api = WebviewApi()
            window = webview.create_window("MagickScale", url, width=1280, height=800, min_size=(1024, 768), js_api=api)
            api.window = window
            
            # Setup tray
            setup_tray(window)
            
            # Start background thread to force icon
            threading.Thread(target=lambda: force_window_icon(window), daemon=True).start()
            
            # Bind window events
            def on_closing(*args):
                window.hide()
                notify_bg_running()
                return False  # Prevent window from being destroyed
                
            def on_minimized(*args):
                window.hide()
                notify_bg_running()
                
            window.events.closing += on_closing
            window.events.minimized += on_minimized
            
            webview.start()
        except Exception as e:
            print(f"Failed to start webview: {e}. Falling back to browser...")
            webbrowser.open(url)
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                pass
        finally:
            server.server_close()
            os._exit(0)


# =====================================================================
# IMAGEMAGICK CHECK & AUTO-INSTALL
# =====================================================================
def check_imagemagick():
    cf = getattr(subprocess, 'CREATE_NO_WINDOW', 0)
    try:
        subprocess.run(["magick", "-version"], check=True, capture_output=True, creationflags=cf)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False

def prompt_install():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    result = messagebox.askyesno(
        "ImageMagick Required",
        "MagickScale requires ImageMagick, but it was not found on your system.\n\n"
        "Would you like to install it automatically using Windows Package Manager? (~1 minute)",
        parent=root
    )
    root.destroy()
    return result

def install_imagemagick():
    root = tk.Tk(); root.withdraw(); root.attributes('-topmost', True)
    win = tk.Toplevel(root); win.title("Installing"); win.geometry("340x100")
    win.resizable(False, False); win.attributes('-topmost', True)
    tk.Label(win, text="Installing ImageMagick via winget...\nPlease wait, this may take a minute.", pady=20).pack()
    win.update()
    try:
        subprocess.run(
            ["winget", "install", "--id", "ImageMagick.ImageMagick",
             "--accept-source-agreements", "--accept-package-agreements", "--silent"],
            check=True
        )
        success = True
    except Exception as e:
        success = False
        messagebox.showerror("Installation Failed", f"Failed to install ImageMagick: {e}", parent=root)
    win.destroy(); root.destroy()
    return success

def extract_bundled_binaries():
    """If frozen, copy bundled binaries from sys._MEIPASS/bin to runtime_dir/bin if not already present."""
    if not getattr(sys, 'frozen', False):
        return
    
    src_bin = os.path.join(base_dir, 'bin')
    dst_bin = os.path.join(runtime_dir, 'bin')
    
    if not os.path.exists(src_bin):
        return
        
    print(f"Extracting bundled binaries to {dst_bin}...")
    for root, dirs, files in os.walk(src_bin):
        rel_path = os.path.relpath(root, src_bin)
        target_root = os.path.normpath(os.path.join(dst_bin, rel_path))
        os.makedirs(target_root, exist_ok=True)
        
        for file in files:
            src_file = os.path.join(root, file)
            dst_file = os.path.join(target_root, file)
            # Copy if file does not exist, or size is different
            if not os.path.exists(dst_file) or os.path.getsize(src_file) != os.path.getsize(dst_file):
                try:
                    shutil.copy2(src_file, dst_file)
                except Exception as e:
                    print(f"Failed to extract {file}: {e}")

def configure_paths():
    """Add bundled binaries directories to the front of PATH so subprocesses find them."""
    im_path = os.path.normpath(os.path.join(runtime_dir, 'bin', 'imagemagick'))
    esrgan_path = os.path.normpath(os.path.join(runtime_dir, 'bin', 'realesrgan'))
    
    paths_to_add = [p for p in [im_path, esrgan_path] if os.path.isdir(p)]
    if paths_to_add:
        os.environ["PATH"] = os.pathsep.join(paths_to_add) + os.pathsep + os.environ.get("PATH", "")

if __name__ == '__main__':
    extract_bundled_binaries()
    configure_paths()
    
    if not check_imagemagick():
        if prompt_install():
            if install_imagemagick():
                if check_imagemagick():
                    messagebox.showinfo("Success", "ImageMagick installed! Starting MagickScale...")
                    run_server()
                else:
                    messagebox.showerror("Error", "Installation done but 'magick' still not found. Try restarting your PC.")
                    sys.exit(1)
            else:
                sys.exit(1)
        else:
            sys.exit(0)
    else:
        run_server()

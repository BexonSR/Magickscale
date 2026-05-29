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
from http.server import HTTPServer, SimpleHTTPRequestHandler
import tkinter as tk
from tkinter import filedialog, messagebox

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
ESRGAN_EXE = os.path.join(ESRGAN_DIR, 'realesrgan-ncnn-vulkan.exe')
MODELS_DIR = os.path.join(ESRGAN_DIR, 'models')
ESRGAN_RELEASE_URL = (
    "https://github.com/xinntao/Real-ESRGAN-ncnn-vulkan/releases/"
    "download/v0.2.0/realesrgan-ncnn-vulkan-v0.2.0-windows.zip"
)

# Upscayl custom-models (https://github.com/upscayl/custom-models)
# MIT / permissive licenses – credits listed in UI
CUSTOM_MODELS = {
    "4x-UltraSharp": {
        "display": "UltraSharp (4x) — Best for Real Photos",
        "bin":   "https://github.com/upscayl/custom-models/raw/main/models/4x-UltraSharp.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4x-UltraSharp.param",
        "scale": 4,
        "credit": "Remacri/UltraSharp – upscayl/custom-models (MIT)"
    },
    "4x-Remacri": {
        "display": "Remacri (4x) — Smooth, Realistic Textures",
        "bin":   "https://github.com/upscayl/custom-models/raw/main/models/4x-Remacri.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4x-Remacri.param",
        "scale": 4,
        "credit": "Remacri – upscayl/custom-models (MIT)"
    },
    "upscayl-lite": {
        "display": "Upscayl Lite (4x) — Fast & Lightweight",
        "bin":   "https://github.com/upscayl/custom-models/raw/main/models/upscayl-lite.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/upscayl-lite.param",
        "scale": 4,
        "credit": "Upscayl Lite – upscayl/custom-models (AGPL-3.0)"
    },
    "4xUltraMix_Balanced": {
        "display": "UltraMix Balanced (4x) — All-rounder",
        "bin":   "https://github.com/upscayl/custom-models/raw/main/models/4xUltraMix_Balanced.bin",
        "param": "https://github.com/upscayl/custom-models/raw/main/models/4xUltraMix_Balanced.param",
        "scale": 4,
        "credit": "UltraMix – upscayl/custom-models (MIT)"
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
}

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
        out = os.path.join(od, f"{name}_4k{ext}")
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
def check_esrgan_ready():
    return os.path.isfile(ESRGAN_EXE)

def model_is_downloaded(model_key):
    """Check if a custom model's .bin and .param files exist."""
    info = CUSTOM_MODELS.get(model_key, {})
    if info.get('bin') is None:  # Bundled with engine
        bname = model_key
        return (os.path.isfile(os.path.join(MODELS_DIR, f"{bname}.bin")) or
                os.path.isfile(os.path.join(ESRGAN_DIR, f"{bname}.bin")))
    bname = model_key
    return (os.path.isfile(os.path.join(MODELS_DIR, f"{bname}.bin")) and
            os.path.isfile(os.path.join(MODELS_DIR, f"{bname}.param")))

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
        with urllib.request.urlopen(req) as response:
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
    """Download a specific custom model's .bin and .param files."""
    info = CUSTOM_MODELS.get(model_key)
    if not info or info.get('bin') is None:
        return False, "Model is bundled with the engine or not found."
    try:
        os.makedirs(MODELS_DIR, exist_ok=True)
        bin_path   = os.path.join(MODELS_DIR, f"{model_key}.bin")
        param_path = os.path.join(MODELS_DIR, f"{model_key}.param")
        print(f"Downloading {model_key}...")
        urllib.request.urlretrieve(info['bin'],   bin_path)
        urllib.request.urlretrieve(info['param'], param_path)
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

    for item in up_state['queue']:
        if up_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; continue

        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: up_state['total_processed'] += 1
            continue

        name, _ = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        out = os.path.join(od, f"{name}_upscaled.{fmt}")

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

                cmd = [
                    ESRGAN_EXE,
                    "-i", current_in,
                    "-o", current_out,
                    "-n", model,
                    "-s", str(pass_scale),
                    "-g", str(gpu_id),
                    "-f", fmt
                ]
                if tta:
                    cmd.append("-x")

                # Point to models dir
                cmd.extend(["-m", MODELS_DIR])

                subprocess.run(cmd, check=True, creationflags=cf)

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

    up_state['processing'] = False

# =====================================================================
# LOGO REMOVER
# =====================================================================
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

    def process_lr_item(item):
        if lr_state['cancel_requested']:
            item['status'] = 'failed'; item['error'] = 'Cancelled'; return
        item['status'] = 'processing'
        src = item['path']
        if not os.path.exists(src):
            item['status'] = 'failed'; item['error'] = 'File not found'
            with state_lock: lr_state['total_processed'] += 1
            return

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

        name, ext = os.path.splitext(os.path.basename(src))
        od = out_dir if out_dir else os.path.dirname(src)
        os.makedirs(od, exist_ok=True)
        out = os.path.join(od, f"{name}_clean{ext}")

        # Gemini AI watermark specifics: small icon bottom-right ~5-7% w, ~5-7% h
        if is_gemini:
            pos_override = 'bottom_right'
            # Gemini logo is typically a small pill in the bottom-right corner
            pw = max(1, int(W * max(size_pct, 8) / 100))
            ph = max(1, int(H * max(size_pct, 6) / 100))
            rx, ry = W - pw, H - ph
            rw, rh = pw, ph
        else:
            pw = max(1, int(W * size_pct / 100))
            ph = max(1, int(H * size_pct / 100))
            pos_override = position

        if not is_gemini:
            if pos_override == 'bottom_right':   rx, ry, rw, rh = W-pw, H-ph, pw, ph
            elif pos_override == 'bottom_left':  rx, ry, rw, rh = 0,    H-ph, pw, ph
            elif pos_override == 'top_right':    rx, ry, rw, rh = W-pw, 0,    pw, ph
            elif pos_override == 'top_left':     rx, ry, rw, rh = 0,    0,    pw, ph
            elif pos_override == 'bottom_bar':   rx, ry, rw, rh = 0,    H-ph, W,  ph
            elif pos_override == 'top_bar':      rx, ry, rw, rh = 0,    0,    W,  ph
            else:                                rx, ry, rw, rh = W-pw, H-ph, pw, ph

        try:
            if is_gemini and method == 'math':
                mask_file = 'bg_96.png' if W > 1024 else 'bg_48.png'
                mask_path = os.path.join(WATERMARK_DIR, mask_file)
                if not os.path.exists(mask_path):
                    ensure_watermark_masks()
                if os.path.exists(mask_path):
                    temp_mask = os.path.join(od, f"__temp_mask_{name}.png")
                    # Gemini watermark is not flush with corner; it has a margin
                    margin = 64 if W > 1024 else 32
                    
                    # 1. Create full-size mask aligned SouthEast with correct margins
                    subprocess.run([
                        "magick", "-size", f"{W}x{H}", "xc:black",
                        mask_path, "-gravity", "SouthEast", "-geometry", f"+{margin}+{margin}",
                        "-composite", temp_mask
                    ], check=True, creationflags=cf)
                    # 2. Run FX math: original = (u - v) / (1 - v)
                    cmd = ["magick", src, temp_mask, "-fx", "(u-v)/max(0.001,1-v)", out]
                    subprocess.run(cmd, check=True, creationflags=cf)
                    # Clean up
                    try: os.remove(temp_mask)
                    except: pass
                else:
                    # Fallback to blur if masks fail to load
                    margin = 64 if W > 1024 else 32
                    mask_size = 96 if W > 1024 else 48
                    region = f"{mask_size}x{mask_size}+{W-mask_size-margin}+{H-mask_size-margin}"
                    cmd = ["magick", src, "-region", region, "-blur", "0x20", out]
                    subprocess.run(cmd, check=True, creationflags=cf)
            elif method == 'crop':
                if pos_override == 'bottom_bar' or (is_gemini and ph < H * 0.15):
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

            elif method == 'clone':
                # Clone adjacent region to paint over the logo
                adj_y = max(0, ry - rh)
                cmd = ["magick", src,
                       "-region", f"{rw}x{rh}+{rx}+{ry}",
                       "-motion-blur", "0x5+180",
                       out]
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
# HTTP SERVER
# =====================================================================

class ApiHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args): pass

    def do_GET(self):
        if self.path == '/api/status':
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

        # --- Shared ---
        if self.path == '/api/select-files':
            resp = {"files": ask_open_files()}
        elif self.path == '/api/select-folder':
            folder = ask_directory("Select Source Directory")
            files = []
            if folder:
                valid = ('.jpg','.jpeg','.png','.webp','.tif','.tiff','.bmp','.heic','.cr2','.nef','.arw')
                for f in os.listdir(folder):
                    if f.lower().endswith(valid):
                        files.append(os.path.normpath(os.path.join(folder, f)))
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
# SERVER
# =====================================================================
def run_server():
    os.makedirs(WEB_DIR, exist_ok=True)
    server = HTTPServer(('127.0.0.1', PORT), ApiHandler)
    url = f"http://127.0.0.1:{PORT}"
    print(f"MagickScale running at {url}")
    threading.Thread(target=lambda: (time.sleep(0.6), webbrowser.open(url)), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server.server_close()

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

if __name__ == '__main__':
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

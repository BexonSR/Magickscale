import os
from PIL import Image
import numpy as np
import shutil

# Make a dummy watermarked image to test with
W, H = 512, 512
img = np.zeros((H, W, 3), dtype=np.uint8)
img[:,:,:] = [100, 150, 200]  # solid blueish color

# apply dummy mask watermark
mask_size = 48
margin = 32
x0 = W - margin - mask_size
y0 = H - margin - mask_size
mask = np.array(Image.open('mask_bg_48.png'))
alpha = mask[:,:,0] / 255.0
alpha_3d = alpha[:,:,np.newaxis]
region = img[y0:y0+mask_size, x0:x0+mask_size]
# composite = bg*(1-a) + fg*a (fg=255)
region_wm = region * (1 - alpha_3d) + 255.0 * alpha_3d
img[y0:y0+mask_size, x0:x0+mask_size] = region_wm.astype(np.uint8)

Image.fromarray(img).save('test_src.png')

def remove_watermark(src, out, W, H, mask_path, mask_size, margin):
    from PIL import Image
    import numpy as np
    
    img_pil = Image.open(src).convert('RGB')
    mask_pil = Image.open(mask_path).convert('RGB')
    
    img_arr = np.array(img_pil, dtype=np.float32)
    mask_arr = np.array(mask_pil, dtype=np.float32)
    
    alpha = mask_arr[:, :, 0] / 255.0
    alpha_3d = alpha[:, :, np.newaxis]
    
    x0 = W - margin - mask_size
    y0 = H - margin - mask_size
    
    # Extract the region
    region = img_arr[y0:y0+mask_size, x0:x0+mask_size]
    
    # Apply reverse alpha blending
    # original = (composite - 255 * a) / (1 - a)
    denom = 1.0 - alpha_3d
    denom = np.where(denom < 1e-6, 1e-6, denom)
    
    original = (region - 255.0 * alpha_3d) / denom
    original = np.clip(np.round(original), 0, 255)
    
    # Put it back
    img_arr[y0:y0+mask_size, x0:x0+mask_size] = original
    
    res_pil = Image.fromarray(img_arr.astype(np.uint8))
    res_pil.save(out, 'PNG')

remove_watermark('test_src.png', 'test_out.png', W, H, 'mask_bg_48.png', mask_size, margin)
print('Done. Checking max diff...')
out_img = np.array(Image.open('test_out.png'))
orig_img = np.zeros((H,W,3), dtype=np.uint8)
orig_img[:,:,:] = [100, 150, 200]
print('Max diff:', np.abs(out_img.astype(int) - orig_img.astype(int)).max())

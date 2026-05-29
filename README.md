# MagickScale

> Status: Beta v1.0

MagickScale is an offline desktop image processing toolkit built for creators, designers, and everyday users. It combines AI-powered enhancement tools with practical image utilities such as slicing, merging, conversion, overlays, and experimental watermark removal, all accessible through a modern and easy-to-use interface.

**Works entirely offline. No cloud uploads, accounts, or subscriptions required.**

## Features

### AI Upscaler

Enhance image quality and increase resolution using Real-ESRGAN. Supports multiple AI models and scaling options for photos, artwork, anime, and digital illustrations.

### Image Slicer

Split images into custom grids or create Steam Artwork Showcase layouts with precise slicing controls.

### Experimental Watermark & Logo Removal

Attempt to remove logos, watermarks, and unwanted image elements using reverse alpha-blending and image reconstruction techniques. Results may vary depending on image complexity.

### Image Merger

Combine images vertically, horizontally, or in custom grid layouts with flexible output settings.

### Image Overlay

Add logos, watermarks, or custom overlays to images with live preview support.

### Format Converter

Convert images between PNG, JPG, JPEG, WebP, AVIF, BMP, and other popular formats with adjustable quality settings.

## Prerequisites

### Windows

If you downloaded the portable release:

1. Install ImageMagick.
2. Launch `MagickScale.exe`.
3. The interface will automatically open in your default web browser.

### Linux / macOS

Requirements:

* Python 3.8+
* ImageMagick

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the application:

```bash
./run.sh
```

Or:

```bash
python app.py
```

## Installing ImageMagick

### Windows

Download and install ImageMagick from:

https://imagemagick.org/script/download.php#windows

During installation, enable:

* Add application directory to your system PATH

### Ubuntu / Debian

```bash
sudo apt install imagemagick
```

### macOS

```bash
brew install imagemagick
```

## Screenshot

Add application screenshots here.

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

© 2026 Senila Ranvin

# MagickScale

<p align="center">
  <img src="image/Screenshot%20(489)_upscaled_4k_converted.webp" width="100%">
</p>

<p align="center">
  <strong>Offline AI-Powered Image Suite</strong>
</p>

<p align="center">
  AI Upscaling • Downscaling • Watermark Removal • Image Slicing • Merging • Conversion • Overlays
</p>

---

> **Status:** Beta v1.0.0

MagickScale is an offline desktop image processing toolkit designed for creators, designers, artists, and everyday users. It combines AI-powered image enhancement with practical image utilities inside a modern desktop interface.

Unlike many online tools, MagickScale runs entirely on your machine. No accounts, subscriptions, or cloud uploads are required.

## Features

### AI Upscaler

Enhance image quality and increase resolution using Real-ESRGAN.

* Multiple AI models
* Anime support
* Artwork support
* Photo enhancement
* Batch processing
* Custom model support

### Downscaler

Reduce image resolution while preserving quality.

* 4K presets
* Custom resolutions
* Multiple resampling filters
* Batch processing
* GPU acceleration support

### Experimental Watermark & Logo Removal

Attempts to remove:

* Watermarks
* Logos
* Embedded image marks

Results vary depending on image complexity and watermark placement.

### Metadata Remover

Remove metadata from images for privacy and cleaner file distribution.

### Image Slicer

Split images into:

* Custom grids
* Steam Artwork Showcase layouts
* Equal sections
* Custom slice dimensions

### Image Merger

Combine multiple images:

* Horizontally
* Vertically
* Grid layouts

### Image Overlay

Apply:

* Logos
* Watermarks
* Branding overlays
* Custom graphics

### Format Converter

Convert between popular image formats:

* PNG
* JPG
* JPEG
* WebP
* AVIF
* BMP

and more.

### Video Processor

Basic video processing tools integrated into the suite.

### Custom AI Models

Supports external Real-ESRGAN models.

Download custom models:

https://github.com/upscayl/custom-models

Place `.param` and `.bin` files inside:

```text
bin/realesrgan/models/
```

Example:

```text
bin/realesrgan/models/my_model.param
bin/realesrgan/models/my_model.bin
```

You can also configure an external models directory from the Settings page.

---

# Installation

## Windows

### Portable Release

1. Download the latest release.
2. Launch `MagickScale_setup-v###.exe`.
Thats it, there you go..! (Currently only tested in Windows 11.But it should work fine in windows 10 too..)

---

## Linux 
(Didn't tesed on These platforms yet. But it should work.




maybe)

### Requirements

* Python 3.8+ (Automatically installing via setup.sh)
* ImageMagick (Automatically installing via setup.sh)


### Optional Native Window Support

Ubuntu / Debian:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0
```

Arch Linux:

```bash
sudo pacman -S python-gobject webkit2gtk
```

If unavailable, MagickScale automatically falls back to browser mode.

### Run

```bash
git clone https://github.com/BexonSR/MagickScale
cd MagickScale
chmod +x setup.sh
./setup.sh
```
---

## macOS

Install ImageMagick:

```bash
brew install imagemagick
```

Run:

```bash
pip install -r requirements.txt
python app.py
```

---

# First Launch

During the first launch, MagickScale may download required AI components automatically.

On Linux, the application automatically downloads the compatible Real-ESRGAN binary and configures it for use.

---
# All images contain in image dir upscaled 4x->downscaled HD->converted to .webp via magickscale

# Screenshots

<p align="center">
  <img src="image/Screenshot%20(480)_upscaled_4k_converted.webp" width="140">
  <img src="image/Screenshot%20(481)_upscaled_4k_converted.webp" width="140">
  <img src="image/Screenshot%20(482)_upscaled_4k_converted.webp" width="140">
  <img src="image/Screenshot%20(483)_upscaled_4k_converted.webp" width="140">
</p>

---

# Privacy

MagickScale processes images locally on your device.

Your files are not uploaded to external servers.

---

# Security

The Windows release has been scanned using VirusTotal.

VirusTotal Report:

https://www.virustotal.com/gui/file/6da81703556dfb85b6660d14c085a3dfdcdada85d49eed2d3230c9fc5d041ccc

PyInstaller-based applications occasionally trigger false positives because they bundle Python runtimes and may launch local interfaces.

Users are encouraged to inspect both the VirusTotal report and the source code.

<p align="left">
  <img src="images/Screenshot%20(416).png" width="180">
</p>

---

# Roadmap

Future improvements may include:

* Additional AI models
* Faster processing pipeline
* Advanced video tools
* Additional image editing utilities
* More export formats

---

# License

Licensed under the MIT License.

See the LICENSE file for details.

© 2026 Senila Ranvin

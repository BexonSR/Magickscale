# MagickScale 


<p align='center'>
   <img src="images/Screenshot%20(417).png" width="100%">
</p>

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

## Coustom Models 

<br><p align='left'>
   <img src="images/Screenshot%20(415).png" width="80%">
</p>

https://github.com/upscayl/custom-models use this link. after downloading it you must put all .bin and .param files in this path:-bin/realesrgan/models/

Ex:-
> ~/Magickscale/bin/realesrgan/models/trump.bin
> ~/Magickscale/bin/realesrgan/models/trump.param

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
cd ~
git clone https://github.com/BexonSR/Magickscale
cd Magickscale
pip install -r requirements.txt
```

Run the application:

```bash
./run.sh #idk why i create this but anyway you can use just python app.py
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
<p align="center">
  <img src="images/Screenshot%20(417).png" width="140">
  <img src="images/Screenshot%20(418).png" width="140">
  <img src="images/Screenshot%20(419).png" width="140">
  <img src="images/Screenshot%20(420).png" width="140">
  <img src="images/Screenshot%20(421).png" width="140">
  <img src="images/Screenshot%20(422).png" width="140">
  <img src="images/Screenshot%20(423).png" width="140">
</p>

## Security

The release executable has been scanned with VirusTotal.

VirusTotal Report:
https://www.virustotal.com/gui/file/6da81703556dfb85b6660d14c085a3dfdcdada85d49eed2d3230c9fc5d041ccc?nocache=1
Please note that PyInstaller-packed executables occasionally trigger false positives from some antivirus vendors.[4/71]
* usually excutable that opens website got this warnings idk why. you can chek youself. all codes are here.
<p align='left'>
   <img src="images/Screenshot%20(416).png" width="160">
</p>


## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

© 2026 Senila Ranvin

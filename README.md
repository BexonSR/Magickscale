# MagickScale

MagickScale is a powerful, AI-driven offline application designed for enhancing and processing images. It bundles upscaling, background removal (watermark/logo removal), slicing for Steam artwork, overlay generation, format conversion, and more, all with an interactive UI.

## Features
* **AI Upscaler**: Harnesses the power of Real-ESRGAN to dramatically increase image resolution (up to 16x) with high detail.
* **Image Slicer**: Specialized slicing algorithms, including a native Steam Artwork template generator to easily create panoramic profile showcases.
* **Logo/Watermark Remover**: Cleanly remove watermarks (including Gemini visible watermarks) using math-based reverse alpha-blending and other techniques.
* **Image Merger**: Easily combine images vertically, horizontally, or in custom grid layouts.
* **Image Overlay**: Quickly brand images with watermarks or logos with an instant live preview.
* **Format Converter**: Batch convert images between PNG, JPG, WebP, AVIF, and more with quality sliders.

## Prerequisites
* **Python 3.8+** (for running from source on Linux/macOS)
* **ImageMagick** (required for Slicer, Merger, Overlay, Converter, and Logo Remover)

### Installing ImageMagick
- **Windows**: [Download ImageMagick for Windows](https://imagemagick.org/script/download.php#windows)
- **Linux (Ubuntu/Debian)**: `sudo apt install imagemagick`
- **macOS**: `brew install imagemagick`

## Running on Windows
If you downloaded the `.exe` portable release:
1. Double click `MagickScale.exe`.
2. The UI will automatically launch in your web browser.

## Running on Linux / macOS (From Source)
1. Ensure you have Python and ImageMagick installed.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run the application:
   ```bash
   ./run.sh
   ```
   Or manually:
   ```bash
   python app.py
   ```

## License
Released under the GNU General Public License v3.0 (GPL-3.0). See `LICENSE` for details.

© 2026 Senila R.

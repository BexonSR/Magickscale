#!/usr/bin/env bash
# MagickScale startup script for Linux and macOS

# Check if Python is installed
if ! command -v python3 &> /dev/null
then
    echo "Python3 could not be found. Please install Python3."
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null
then
    echo "pip3 could not be found. Please install pip3."
    exit 1
fi

# Check if ImageMagick is installed
if ! command -v magick &> /dev/null
then
    echo "ImageMagick ('magick') could not be found."
    echo "Please install it: sudo apt install imagemagick (Linux) or brew install imagemagick (macOS)."
    exit 1
fi

# Install requirements
echo "Installing dependencies..."
pip3 install -r requirements.txt

# Run the app
echo "Starting MagickScale..."
python3 app.py

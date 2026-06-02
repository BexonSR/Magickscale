#!/bin/bash

# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Print Header
clear
echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "${BLUE}${BOLD}      MagickScale — Setup Wizard for Linux           ${NC}"
echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "This script will install system dependencies, set up a Python"
echo -e "virtual environment, and configure everything automatically.\n"

# Check if running as root (not recommended for the whole script)
if [ "$EUID" -eq 0 ]; then
   echo -e "${YELLOW}[Warning] Do not run this script as root/sudo directly.${NC}"
   echo -e "It will ask for sudo password only when installing system packages."
   echo -e "Running as root will cause file permission issues. Please run as a normal user.\n"
   exit 1
fi

# Detect package manager and install dependencies
detect_and_install_deps() {
    echo -e "${CYAN}${BOLD}[1/4] Detecting Linux Distribution and Package Manager...${NC}"
    
    if [ -x "$(command -v apt-get)" ]; then
        echo -e "Detected: ${GREEN}Debian/Ubuntu-based system (apt)${NC}"
        echo -e "Updating package index..."
        sudo apt-get update -y
        echo -e "Installing dependencies (Python3, Pip, ImageMagick, WebKit2GTK)..."
        sudo apt-get install -y python3 python3-pip python3-venv imagemagick \
            python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.0 || \
        sudo apt-get install -y python3 python3-pip python3-venv imagemagick \
            python3-gi python3-gi-cairo gir1.2-gtk-3.0 gir1.2-webkit2-4.1
            
    elif [ -x "$(command -v dnf)" ]; then
        echo -e "Detected: ${GREEN}Fedora/RHEL-based system (dnf)${NC}"
        echo -e "Installing dependencies (Python3, Pip, ImageMagick, WebKit2GTK)..."
        sudo dnf install -y python3 python3-pip ImageMagick python3-gobject webkit2gtk4.0 || \
        sudo dnf install -y python3 python3-pip ImageMagick python3-gobject webkit2gtk4.1
        
    elif [ -x "$(command -v pacman)" ]; then
        echo -e "Detected: ${GREEN}Arch-based system (pacman)${NC}"
        echo -e "Installing dependencies (Python3, Pip, ImageMagick, WebKit2GTK)..."
        sudo pacman -Syu --noconfirm python python-pip imagemagick python-gobject webkit2gtk
        
    elif [ -x "$(command -v zypper)" ]; then
        echo -e "Detected: ${GREEN}openSUSE-based system (zypper)${NC}"
        echo -e "Installing dependencies (Python3, Pip, ImageMagick, WebKit2GTK)..."
        sudo zypper install -y python3 python3-pip ImageMagick python3-gobject typelib-1_0-WebKit2-4_0
        
    else
        echo -e "${RED}[Error] Unsupported package manager. Please install Python3, Pip, ImageMagick, and WebKit2GTK manually.${NC}"
        exit 1
    fi
    echo -e "${GREEN}System dependencies installed successfully!${NC}\n"
}

# Create Python Virtual Environment
setup_venv() {
    echo -e "${CYAN}${BOLD}[2/4] Setting up Python Virtual Environment (venv)...${NC}"
    if [ -d "venv" ]; then
        echo -e "Virtual environment 'venv' already exists. Re-using it..."
    else
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip and install requirements
    echo -e "Upgrading pip..."
    pip install --upgrade pip
    
    echo -e "Installing Python requirements from requirements.txt..."
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
    else
        pip install pywebview pystray Pillow
    fi
    
    echo -e "${GREEN}Python virtual environment configured successfully!${NC}\n"
}

# Create wrapper script
create_run_script() {
    echo -e "${CYAN}${BOLD}[3/4] Creating executable wrapper script (run.sh)...${NC}"
    
    # Write run.sh file with LF endings
    with open("run.sh", "w", newline="\n", encoding="utf-8") as rf:
        rf.write("#!/bin/bash\n")
        rf.write("# Activate virtual environment and run the app\n")
        rf.write("SRC_DIR=\"$( cd \"$( dirname \"${BASH_SOURCE[0]}\" )\" && pwd )\"\n")
        rf.write("cd \"$SRC_DIR\"\n")
        rf.write("source venv/bin/activate\n")
        rf.write("python app.py\n")

    chmod +x run.sh
    echo -e "${GREEN}Wrapper script 'run.sh' created!${NC}\n"
}

# Register command alias globally for bash, zsh, and fish
register_alias() {
    echo -e "${CYAN}${BOLD}[4/4] Registering 'magickscale' command alias...${NC}"
    local run_path
    run_path="$(pwd)/run.sh"

    # Bash alias
    if [ -f "$HOME/.bashrc" ]; then
        if ! grep -q "alias magickscale=" "$HOME/.bashrc"; then
            echo -e "\n# MagickScale Command Alias" >> "$HOME/.bashrc"
            echo "alias magickscale=\"$run_path\"" >> "$HOME/.bashrc"
            echo -e "Registered alias in ${GREEN}~/.bashrc${NC}"
        else
            echo -e "Alias already exists in ${GREEN}~/.bashrc${NC}"
        fi
    fi

    # Zsh alias
    if [ -f "$HOME/.zshrc" ]; then
        if ! grep -q "alias magickscale=" "$HOME/.zshrc"; then
            echo -e "\n# MagickScale Command Alias" >> "$HOME/.zshrc"
            echo "alias magickscale=\"$run_path\"" >> "$HOME/.zshrc"
            echo -e "Registered alias in ${GREEN}~/.zshrc${NC}"
        else
            echo -e "Alias already exists in ${GREEN}~/.zshrc${NC}"
        fi
    fi

    # Fish alias
    if [ -d "$HOME/.config/fish" ]; then
        mkdir -p "$HOME/.config/fish/functions"
        with open(os.path.expanduser("~/.config/fish/functions/magickscale.fish"), "w", newline="\n", encoding="utf-8") as ff:
            ff.write("function magickscale --description 'Launch MagickScale'\n")
            ff.write(f"    {run_path} $argv\n")
            ff.write("end\n")
        echo -e "Registered custom command in ${GREEN}~/.config/fish/functions/magickscale.fish${NC}"
    fi

    echo -e "${GREEN}Command alias registered successfully!${NC}\n"
}

# Run setup steps
detect_and_install_deps
setup_venv
create_run_script
register_alias

# Finish Setup
echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "${GREEN}${BOLD}           Setup Completed Successfully!             ${NC}"
echo -e "${BLUE}${BOLD}=====================================================${NC}"
echo -e "To launch MagickScale, restart your terminal and type:"
echo -e "   ${CYAN}${BOLD}magickscale${NC}"
echo -e "\nHave fun processing images! ✨\n"

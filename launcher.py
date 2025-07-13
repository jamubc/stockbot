"""
Stockbot Launcher - Main launcher application for Solana tools.

This module provides:
- Configuration management with live updates from GitHub
- Dependency checking and installation
- Module downloading and verification
- GUI launcher for available tools

The launcher automatically updates configuration files and downloads
required modules from the remote repository.
"""

import dearpygui.dearpygui as dpg
import importlib
import threading
import time
import os
import subprocess
import json
import requests

# -------------------------------------
# Global Variables & Initial Config Setup
# -------------------------------------
CONFIG_URL = "https://raw.githubusercontent.com/jamubc/stockbot/refs/heads/main/config.json"
python_results = []
results = []
requirements_check_results = ""
module_results = {}

# Download the live config file from GitHub.
def update_config():
    """Download and update the configuration file from the remote repository."""
    try:
        print("Downloading live config...")
        response = requests.get(CONFIG_URL, timeout=30)
        response.raise_for_status()  # Ensure a good response
        with open("config.json", "wb") as f:
            f.write(response.content)
        print("Config updated successfully.")
        return True
    except requests.RequestException as e:
        print(f"Failed to update config (network error): {e}")
        return False
    except Exception as e:
        print(f"Failed to update config: {e}")
        return False

# Run pip install -r requirements.txt (using the current Python interpreter).
def install_requirements_file():
    """Install Python packages from requirements.txt file."""
    try:
        print("Running pip install -r requirements.txt ...")
        process = subprocess.run(
            ["python", "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if process.returncode == 0:
            print("Requirements installed successfully.")
        else:
            print("Failed to install requirements:", process.stderr)
    except subprocess.TimeoutExpired:
        print("Pip install timed out after 5 minutes")
    except Exception as e:
        print(f"Error during pip install: {e}")

# Load the config file (which might have been updated).
def load_config():
    """Load configuration from config.json file."""
    try:
        with open('config.json', 'r') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print("Config file not found")
        return {}
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}")
        return {}

# Load additional requirements based on the config.
def load_requirements(config):
    """Download and load additional requirements from remote sources."""
    global requirements_check_results
    python_results.clear()
    files_status = []
    
    # For extra python libraries/modules
    for req in config.get("python_requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        
        if not file_name:
            continue
            
        # Skip if no valid source URL is provided.
        if not source_url or source_url.lower() == "none":
            python_results.append(f"{file_name}: No valid source URL provided")
            continue
            
        if os.path.exists(file_name):
            python_results.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url, timeout=30)
                response.raise_for_status()
                with open(file_name, "wb") as f:
                    f.write(response.content)
                python_results.append(f"{file_name}: Downloaded from server")
            except requests.RequestException as e:
                python_results.append(f"{file_name}: Failed to download (network error: {e})")
            except Exception as e:
                python_results.append(f"{file_name}: Failed to download ({e})")
    
    # For other files, similar logic applies...
    for req in config.get("requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        
        if not file_name:
            continue
            
        if not source_url or source_url.lower() == "none":
            files_status.append(f"{file_name}: No valid source URL provided")
            continue
            
        if os.path.exists(file_name):
            files_status.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url, timeout=30)
                response.raise_for_status()
                with open(file_name, "wb") as f:
                    f.write(response.content)
                files_status.append(f"{file_name}: Downloaded from server")
            except requests.RequestException as e:
                files_status.append(f"{file_name}: Failed to download (network error: {e})")
            except Exception as e:
                files_status.append(f"{file_name}: Failed to download ({e})")
                
    requirements_check_results = "\n".join(files_status)
    return requirements_check_results


# Check for module presence by trying to import them.
def check_modules():
    """Check if required modules can be imported successfully."""
    module_results.clear()
    for mod in python_results:
        module_name = mod.split(":")[0]
        try:
            module_obj = importlib.import_module(module_name)
            src = getattr(module_obj, "__file__", "Unknown source")
            module_results[mod] = f"Found: {src}"
        except ImportError as e:
            module_results[mod] = f"Missing: {e}"
        except Exception as e:
            module_results[mod] = f"Error: {e}"
            
        # Update the log widget so the user can see progress.
        if dpg.does_item_exist("log_text"):
            dpg.set_value("log_text", f"Checking {mod}: {module_results[mod]}")
        time.sleep(0.5)
    
    # Hide loading overlay and show results
    if dpg.does_item_exist("loading_overlay"):
        dpg.configure_item("loading_overlay", show=False)
        
    final_results = "\n".join(f"{m}: {status}" for m, status in module_results.items())
    result_text = final_results + "\n\nRequirements Check:\n" + requirements_check_results
    
    if dpg.does_item_exist("result_log"):
        dpg.set_value("result_log", result_text)

# Combined task that runs pip install, updates config, loads requirements and checks modules.
def start_checking_process(sender, app_data, user_data):
    """Start the complete module checking and installation process."""
    if dpg.does_item_exist("loading_overlay"):
        dpg.configure_item("loading_overlay", show=True)
    
    def task():
        """Background task for checking and installing modules."""
        try:
            # Step 1: Install pip packages from requirements.txt.
            install_requirements_file()
            
            # Step 2: Update config from the live URL.
            if update_config():
                config = load_config()
                # Optionally update version information from new config.
                global VERSION
                VERSION = config.get('dev', [{}])[0].get('version', 'Unknown')
            else:
                print("Could not update config from remote. Using local version.")
                config = load_config()  # Fall back to local copy.
                
            # Step 3: Download any additional required files.
            load_requirements(config)
            
            # Step 4: Check that the modules can be imported.
            check_modules()
            
        except Exception as e:
            print(f"Error in checking process: {e}")
            if dpg.does_item_exist("result_log"):
                dpg.set_value("result_log", f"Error during process: {e}")
            if dpg.does_item_exist("loading_overlay"):
                dpg.configure_item("loading_overlay", show=False)
    
    threading.Thread(target=task, daemon=True).start()

# Launch a module in a separate subprocess.
def launch_solpy():
    """Launch the Solana Python module in a separate process."""
    try:
        subprocess.Popen(["python", "modules/solpy.py"])
        print("Launching solpy.py...")
    except FileNotFoundError:
        print("Error: solpy.py not found in modules directory")
    except Exception as e:
        print(f"Error launching solpy.py: {e}")

def launch_button_callback(sender, app_data, user_data):
    """Callback for the launch button."""
    launch_solpy()

# -------------------------------------
# Initial Configuration Load
# -------------------------------------
# If there is no local config file, download it on startup.
if not os.path.exists("config.json"):
    print("No local config found, attempting to download...")
    update_config()

config = load_config()
VERSION = config.get('dev', [{}])[0].get('version', 'Unknown')

# -------------------------------------
# Build the GUI with dearpygui
# -------------------------------------
dpg.create_context()
with dpg.window(label="", width=800, height=500):
    dpg.add_spacer(height=2)
    dpg.add_text("Welcome to the launcher - Launch a tool or check your install using WIZARD")
    dpg.add_button(label="Goto source")
    dpg.add_spacer(height=2)
    dpg.add_text(f"Version: {VERSION}")
    dpg.add_spacer(height=5)
    dpg.add_separator()
    dpg.add_spacer(height=5)
    
    with dpg.tab_bar():
        # --- Launcher Tab ---
        with dpg.tab(label="Launcher"):
            dpg.add_spacer(height=20)
            dpg.add_button(label="Launch Solpy", callback=launch_button_callback)
            dpg.add_spacer(height=20)
            
        # --- Module Checker (Wizard) Tab ---
        with dpg.tab(label="Wizard"):
            dpg.add_text("Press the button to update config,\ninstall requirements, download modules, and check imports.", color=[0, 128, 255])
            # This is the fetch modules button — adjust label as desired.
            dpg.add_button(label="Start Module Check", callback=start_checking_process)
            dpg.add_spacer(height=30)
            dpg.add_text("Status:", tag="log_text")
            dpg.add_separator()
            dpg.add_text("Output:", tag="result_log", wrap=500)
            # Loading overlay group (initially hidden)
            with dpg.child_window(tag="loading_overlay", width=580, height=100):
                dpg.add_text("Operation in progress...", bullet=True, color=[255, 0, 0])
            dpg.configure_item("loading_overlay", show=False)

dpg.create_viewport(title=f"LAUNCHER - - {VERSION}", width=800, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()

while dpg.is_dearpygui_running():
    dpg.render_dearpygui_frame()

dpg.destroy_context()

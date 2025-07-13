"""
Stockbot Launcher Application

This module provides a GUI launcher for the stockbot application suite,
including module management, dependency checking, and application launching.
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
CONFIG_FILE = "config.json"
REQUIREMENTS_FILE = "requirements.txt"
SOLPY_MODULE_PATH = "modules/solpy.py"

# Global state variables
python_results = []
results = []
requirements_check_results = ""
module_results = {}
VERSION = "Unknown"

# Download the live config file from GitHub.
def update_config() -> bool:
    """
    Download the latest configuration file from GitHub.
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        print("Downloading live config...")
        response = requests.get(CONFIG_URL, timeout=30)
        response.raise_for_status()  # Ensure a good response
        with open(CONFIG_FILE, "wb") as f:
            f.write(response.content)
        print("Config updated successfully.")
        return True
    except requests.exceptions.Timeout:
        print("Failed to update config: Request timed out")
        return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to update config: Network error: {e}")
        return False
    except Exception as e:
        print(f"Failed to update config: {e}")
        return False

# Run pip install -r requirements.txt (using the current Python interpreter).
def install_requirements_file():
    """
    Install Python packages from requirements.txt file.
    """
    try:
        print("Running pip install -r requirements.txt ...")
        process = subprocess.run(
            ["python", "-m", "pip", "install", "-r", REQUIREMENTS_FILE],
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout
        )
        if process.returncode == 0:
            print("Requirements installed successfully.")
        else:
            print("Failed to install requirements:", process.stderr)
    except subprocess.TimeoutExpired:
        print("Error during pip install: Process timed out")
    except Exception as e:
        print(f"Error during pip install: {e}")

# Load the config file (which might have been updated).
def load_config() -> dict:
    """
    Load configuration from the config file.
    
    Returns:
        dict: Configuration data
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If config file is invalid JSON
    """
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as config_file:
            return json.load(config_file)
    except FileNotFoundError:
        print(f"Config file {CONFIG_FILE} not found")
        raise
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in config file: {e}")
        raise

# Load additional requirements based on the config.
def load_requirements(config: dict) -> str:
    """
    Load additional requirements from config and download missing files.
    
    Args:
        config (dict): Configuration dictionary
        
    Returns:
        str: Status summary of file operations
    """
    global requirements_check_results
    python_results.clear()
    files_status = []
    
    # For extra python libraries/modules
    python_requirements = config.get("python_requirements", [])
    for req in python_requirements:
        if not isinstance(req, dict):
            continue
            
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
            except requests.exceptions.Timeout:
                python_results.append(f"{file_name}: Failed to download (timeout)")
            except requests.exceptions.RequestException as e:
                python_results.append(f"{file_name}: Failed to download (network error: {e})")
            except Exception as e:
                python_results.append(f"{file_name}: Failed to download ({e})")
    
    # For other files, similar logic applies...
    other_requirements = config.get("requirements", [])
    for req in other_requirements:
        if not isinstance(req, dict):
            continue
            
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
            except requests.exceptions.Timeout:
                files_status.append(f"{file_name}: Failed to download (timeout)")
            except requests.exceptions.RequestException as e:
                files_status.append(f"{file_name}: Failed to download (network error: {e})")
            except Exception as e:
                files_status.append(f"{file_name}: Failed to download ({e})")
                
    requirements_check_results = "\n".join(files_status)
    return requirements_check_results


# Check for module presence by trying to import them.
def check_modules():
    """
    Check if required Python modules can be imported and update UI accordingly.
    """
    module_results.clear()
    for mod in python_results:
        module_name = mod.split(":")[0]
        try:
            module_obj = importlib.import_module(module_name)
            src = getattr(module_obj, "__file__", "Unknown source")
            module_results[mod] = f"Found: {src}"
        except ImportError:
            module_results[mod] = "Missing"
        except Exception as e:
            module_results[mod] = f"Error: {str(e)}"
            
        # Update the log widget so the user can see progress.
        try:
            dpg.set_value("log_text", f"Checking {mod}: {module_results[mod]}")
        except Exception:
            pass  # Handle case where UI element doesn't exist
        time.sleep(0.5)
        
    try:
        dpg.configure_item("loading_overlay", show=False)
    except Exception:
        pass  # Handle case where UI element doesn't exist
        
    final_results = "\n".join(f"{m}: {status}" for m, status in module_results.items())
    result_text = final_results + "\n\nRequirements Check:\n" + requirements_check_results
    
    try:
        dpg.set_value("result_log", result_text)
    except Exception:
        print(result_text)  # Fallback to console output

# Combined task that runs pip install, updates config, loads requirements and checks modules.
def start_checking_process(sender, app_data, user_data):
    """
    Start the module checking process in a background thread.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback  
        user_data: User data passed to the callback
    """
    try:
        dpg.configure_item("loading_overlay", show=True)
    except Exception:
        pass
    
    def task():
        """Background task that performs all checking operations."""
        global VERSION
        
        try:
            # Step 1: Install pip packages from requirements.txt.
            install_requirements_file()
            
            # Step 2: Update config from the live URL.
            if update_config():
                config = load_config()
                # Optionally update version information from new config.
                dev_info = config.get('dev', [{}])
                if dev_info and isinstance(dev_info, list) and len(dev_info) > 0:
                    VERSION = dev_info[0].get('version', 'Unknown')
            else:
                print("Could not update config from remote. Using local version.")
                try:
                    config = load_config()  # Fall back to local copy.
                except (FileNotFoundError, json.JSONDecodeError):
                    print("No valid local config found.")
                    return
                    
            # Step 3: Download any additional required files.
            load_requirements(config)
            
            # Step 4: Check that the modules can be imported.
            check_modules()
            
        except Exception as e:
            print(f"Error in checking process: {e}")
            try:
                dpg.configure_item("loading_overlay", show=False)
                dpg.set_value("result_log", f"Error during checking process: {e}")
            except Exception:
                pass
    
    threading.Thread(target=task, daemon=True).start()

# Launch a module in a separate subprocess.
def launch_solpy():
    """
    Launch the Solana Python module in a separate process.
    """
    try:
        if not os.path.exists(SOLPY_MODULE_PATH):
            print(f"Error: {SOLPY_MODULE_PATH} not found")
            return
            
        subprocess.Popen(["python", SOLPY_MODULE_PATH])
        print("Launching solpy.py...")
    except Exception as e:
        print(f"Error launching solpy.py: {e}")

def launch_button_callback(sender, app_data, user_data):
    """
    Callback for the launch button.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
        user_data: User data passed to the callback
    """
    launch_solpy()

# -------------------------------------
# Initial Configuration Load
# -------------------------------------
def initialize_config():
    """
    Initialize configuration on startup.
    
    Returns:
        dict: Loaded configuration data
    """
    global VERSION
    
    # If there is no local config file, download it on startup.
    if not os.path.exists(CONFIG_FILE):
        print(f"No local config file found. Attempting to download...")
        if not update_config():
            print("Failed to download config. Creating minimal config.")
            # Create a minimal config if download fails
            minimal_config = {
                "dev": [{"version": "Unknown"}],
                "requirements": [],
                "python_requirements": []
            }
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(minimal_config, f, indent=2)
            except Exception as e:
                print(f"Could not create minimal config: {e}")
                return minimal_config

    try:
        config = load_config()
        dev_info = config.get('dev', [{}])
        if dev_info and isinstance(dev_info, list) and len(dev_info) > 0:
            VERSION = dev_info[0].get('version', 'Unknown')
        return config
    except Exception as e:
        print(f"Error loading config: {e}")
        VERSION = "Unknown"
        return {"dev": [{"version": "Unknown"}], "requirements": [], "python_requirements": []}

config = initialize_config()

# -------------------------------------
# Build the GUI with dearpygui
# -------------------------------------
def create_launcher_gui():
    """Create and configure the launcher GUI."""
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
            create_launcher_tab()
            create_wizard_tab()

def create_launcher_tab():
    """Create the launcher tab with application launch buttons."""
    with dpg.tab(label="Launcher"):
        dpg.add_spacer(height=20)
        dpg.add_button(label="Launch Solpy", callback=launch_button_callback)
        dpg.add_spacer(height=20)

def create_wizard_tab():
    """Create the wizard tab for module checking and installation."""
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

def run_launcher():
    """Run the launcher application."""
    try:
        create_launcher_gui()
        
        dpg.create_viewport(title=f"LAUNCHER - - {VERSION}", width=800, height=500)
        dpg.setup_dearpygui()
        dpg.show_viewport()

        while dpg.is_dearpygui_running():
            dpg.render_dearpygui_frame()

    except Exception as e:
        print(f"Error running launcher: {e}")
    finally:
        try:
            dpg.destroy_context()
        except Exception:
            pass

if __name__ == "__main__":
    run_launcher()

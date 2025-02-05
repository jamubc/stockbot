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
    try:
        print("Downloading live config...")
        response = requests.get(CONFIG_URL)
        response.raise_for_status()  # Ensure a good response
        with open("config.json", "wb") as f:
            f.write(response.content)
        print("Config updated successfully.")
        return True
    except Exception as e:
        print(f"Failed to update config: {e}")
        return False

# Run pip install -r requirements.txt (using the current Python interpreter).
def install_requirements_file():
    try:
        print("Running pip install -r requirements.txt ...")
        process = subprocess.run(
            ["python", "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True
        )
        if process.returncode == 0:
            print("Requirements installed successfully.")
        else:
            print("Failed to install requirements:", process.stderr)
    except Exception as e:
        print(f"Error during pip install: {e}")

# Load the config file (which might have been updated).
def load_config():
    with open('config.json', 'r') as config_file:
        return json.load(config_file)

# Load additional requirements based on the config.
def load_requirements(config):
    global requirements_check_results
    python_results.clear()
    files_status = []
    # For extra python libraries/modules
    for req in config.get("python_requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        # Skip if no valid source URL is provided.
        if not source_url or source_url.lower() == "none":
            python_results.append(f"{file_name}: No valid source URL provided")
            continue
        if os.path.exists(file_name):
            python_results.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url)
                response.raise_for_status()
                with open(file_name, "wb") as f:
                    f.write(response.content)
                python_results.append(f"{file_name}: Downloaded from server")
            except Exception as e:
                python_results.append(f"{file_name}: Failed to download ({e})")
    
    # For other files, similar logic applies...
    for req in config.get("requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        if not source_url or source_url.lower() == "none":
            files_status.append(f"{file_name}: No valid source URL provided")
            continue
        if os.path.exists(file_name):
            files_status.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url)
                response.raise_for_status()
                with open(file_name, "wb") as f:
                    f.write(response.content)
                files_status.append(f"{file_name}: Downloaded from server")
            except Exception as e:
                files_status.append(f"{file_name}: Failed to download ({e})")
    requirements_check_results = "\n".join(files_status)
    return requirements_check_results


# Check for module presence by trying to import them.
def check_modules():
    module_results.clear()
    for mod in python_results:
        module_name = mod.split(":")[0]
        try:
            module_obj = importlib.import_module(module_name)
            src = getattr(module_obj, "__file__", "Unknown source")
            module_results[mod] = f"Found: {src}"
        except ImportError:
            module_results[mod] = "Missing"
        # Update the log widget so the user can see progress.
        dpg.set_value("log_text", f"Checking {mod}: {module_results[mod]}")
        time.sleep(0.5)
    dpg.configure_item("loading_overlay", show=False)
    final_results = "\n".join(f"{m}: {status}" for m, status in module_results.items())
    dpg.set_value("result_log", final_results + "\n\nRequirements Check:\n" + requirements_check_results)

# Combined task that runs pip install, updates config, loads requirements and checks modules.
def start_checking_process(sender, app_data, user_data):
    dpg.configure_item("loading_overlay", show=True)
    
    def task():
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
    
    threading.Thread(target=task, daemon=True).start()

# Launch a module in a separate subprocess.
def launch_solpy():
    try:
        subprocess.Popen(["python", "modules/solpy.py"])
        print("Launching solpy.py...")
    except Exception as e:
        print(f"Error launching solpy.py: {e}")

def launch_button_callback(sender, app_data, user_data):
    launch_solpy()

# -------------------------------------
# Initial Configuration Load
# -------------------------------------
# If there is no local config file, download it on startup.
if not os.path.exists("config.json"):
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

import dearpygui.dearpygui as dpg
import importlib
import threading
import time
import os
import subprocess
import json
import requests  # Needed for downloading missing files
import time

# ============================
# Load Configuration and Check Requirements
# ============================


with open('config.json', 'r') as config_file:
    config = json.load(config_file)

# Extract version correctly from the config structure
VERSION = config.get('dev', [{}])[0].get('version', 'Unknown')

python_results = []
results = []

def load_requirements():
    for req in config.get("python_requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        if os.path.exists(file_name):
            python_results.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url)
                response.raise_for_status()  # raise exception for bad response
                with open(file_name, "wb") as f:
                    f.write(response.content)
                python_results.append(f"{file_name}: Downloaded from server")
            except Exception as e:
                python_results.append(f"{file_name}: Failed to download ({e})")

    for req in config.get("requirements", []):
        file_name = req.get("name")
        source_url = req.get("source")
        # Check file existence using the actual file name/path
        if os.path.exists(file_name):
            results.append(f"{file_name}: Loaded locally")
        else:
            try:
                response = requests.get(source_url)
                response.raise_for_status()  # raise exception for bad response
                with open(file_name, "wb") as f:
                    f.write(response.content)
                results.append(f"{file_name}: Downloaded from server")
            except Exception as e:
                results.append(f"{file_name}: Failed to download ({e})")
                
    return "\n".join(results)

# Global dictionary to store module check results.
module_results = {}

# ============================
# Module Checking Functionality
# ============================
def check_modules():
    module_results.clear()
    for mod in python_results:
        try:
            # Attempt to import the module using its name (if applicable)
            module_obj = importlib.import_module(mod.split(":")[0])
            src = getattr(module_obj, "__file__", "Failed!")
            module_results[mod] = f"Found: {src}"
        except ImportError:
            module_results[mod] = "Missing"
        # Update the log widget so the user can see progress.
        dpg.set_value("log_text", f"Checking {mod}: {module_results[mod]}")
        time.sleep(0.5)
    dpg.configure_item("loading_overlay", show=False)
    final_results = "\n".join(f"{m}: {status}" for m, status in module_results.items())
    dpg.set_value("result_log", final_results + "\n\nRequirements Check:\n" + requirements_check_results)

def start_module_check(sender, app_data, user_data):
    dpg.configure_item("loading_overlay", show=True)
    thread = threading.Thread(target=check_modules, daemon=True)
    thread.start()

# ============================
# Launcher Functionality     =
# ============================
def launch_solpy():
    try:
        # Launch the script located in the modules folder.
        subprocess.Popen(["python", "modules/solpy.py"])
        print("Launching solpy.py...")
    except Exception as e:
        print(f"Error launching solpy.py: {e}")

def launch_button_callback(sender, app_data, user_data):
    launch_solpy()

# ============================
# Build the Combined GUI
# ============================
dpg.create_context()
unique_tag = dpg.generate_uuid()
with dpg.window(label="", width=800, height=500):
    dpg.add_spacer(height=2)
    dpg.add_text("Welcome to the launcher - Launch a tool or check your install using WIZARD ")
    dpg.add_button(label="Goto source")
    dpg.add_spacer(height=2)
    dpg.add_text(f"Version: {VERSION} & {str(dpg.get_value(unique_tag))}")
    dpg.add_spacer(height=5)
    dpg.add_separator(label="")
    dpg.add_spacer(height=5)
    with dpg.tab_bar():
        # --- Launcher Tab ---
        with dpg.tab(label="Launcher"):
            dpg.add_spacer(height=20)
            dpg.add_button(label="Launch Solpy", callback=launch_button_callback)
            dpg.add_spacer(height=20)
        # --- Module Checker Tab ---
        with dpg.tab(label="Wizard"):
            dpg.add_text("Press button to fetch requirements", color=[0, 128, 255])
            dpg.add_button(label="Start Module Check", callback=start_module_check)
            dpg.add_spacer(height=30)
            dpg.add_text("Status:", tag="log_text")
            dpg.add_separator()
            dpg.add_text("Output:", tag="result_log", wrap=500)
            # Loading overlay group (initially hidden)
            with dpg.child_window(tag="loading_overlay", width=580, height=100):
                dpg.add_text("Started tool", bullet=True, color=[255, 0, 0])
            dpg.configure_item("loading_overlay", show=False)
            
# ============================
# Set Up Viewport and Start GUI
# ============================
dpg.create_viewport(title=(f"LAUNCHER - - {VERSION}"), width=800, height=500)
dpg.setup_dearpygui()
dpg.show_viewport()

# Use a manual render loop to update the progress bar.
while dpg.is_dearpygui_running():

    dpg.render_dearpygui_frame()

dpg.destroy_context()

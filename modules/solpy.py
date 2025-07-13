"""
Solana Networker - A GUI application for Solana wallet management and balance checking.

This module provides functionality for:
- Wallet management (import, export, generate)
- Balance checking for SOL and SPL tokens
- Transaction sending (simulated)
- Secure key management with encryption

Security Note: This is a demonstration application. For production use,
implement proper authentication and key management systems.
"""

import os
import subprocess
import json
import base64
import requests
import dearpygui.dearpygui as dpg
from solders.pubkey import Pubkey
from solana.rpc.api import Client
#from solana.keypair import Keypair
from cryptography.fernet import Fernet

VERSION_ = "Solana Networker (1a_2025)"

# ---------------------------
# Secure Key Management Setup
# ---------------------------
KEY_FILE = "wallet_key.key"
if os.path.exists(KEY_FILE):
    with open(KEY_FILE, "rb") as f:
        encryption_key = f.read()
else:
    encryption_key = Fernet.generate_key()
    with open(KEY_FILE, "wb") as f:
        f.write(encryption_key)
fernet = Fernet(encryption_key)

def encrypt_private_key(pk: str) -> str:
    """Encrypt a private key using Fernet encryption."""
    return fernet.encrypt(pk.encode()).decode()

def decrypt_private_key(encrypted_pk: str) -> str:
    """Decrypt a private key using Fernet encryption."""
    return fernet.decrypt(encrypted_pk.encode()).decode()

def login():
    """Handle user authentication with configurable credentials."""
    username = dpg.get_value("username")
    password = dpg.get_value("password")
    
    # TODO: Replace with proper authentication system
    # For now, allow any non-empty credentials for demo purposes
    if username and password:
        dpg.delete_item("authenticationWindow")
    else:
        dpg.set_value("result_text", "Please enter both username and password")

# ---------------------------
# Wallets Dictionary (with encrypted private keys)
# Example wallets for demonstration purposes
# ---------------------------
wallets = {
    "wallet1": {
        "address": "YourWalletAddressHere",
        "private_key": encrypt_private_key("YourPrivateKeyHere"),
        "public_key": "YourPublicKeyHere",
    },
    "wallet2": {
        "address": "AnotherWalletAddressHere", 
        "private_key": encrypt_private_key("AnotherPrivateKeyHere"),
        "public_key": "AnotherPublicKeyHere",
    }
}

# ---------------------------
# Settings and Context
# ---------------------------
UI_WIDTH = 250  # Consistent UI element width
dpg.create_context()

with dpg.font_registry():
    font_path = "/System/Library/Fonts/Supplemental/Optima.ttc"  # For macOS
    # For Windows you might use: "C:/Windows/Fonts/arial.ttf"
    if os.path.exists(font_path):
        default_font = dpg.add_font(font_path, 19)
        dpg.bind_font(default_font)

# ---------------------------
# Utility Callback Functions
# ---------------------------
def temp_callback(sender, app_data):
    """Temporary callback function for menu items under development."""
    print(f"Button '{sender}' pressed - functionality not yet implemented")

def write_to_clipboard(output):
    """Write output to system clipboard (macOS specific implementation)."""
    try:
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(output.encode('utf-8'))
    except Exception as e:
        print(f"Failed to copy to clipboard: {e}")

def enter():
    """Check if user has agreed to connect to network."""
    # Returns True if the "Connect to network" checkbox is checked.
    understand = dpg.get_value("understand_checkbox")
    return bool(understand)

def wallet_combo_callback(sender, app_data):
    """Handle wallet selection from dropdown menu."""
    # When a wallet is selected from the dropdown, update the wallet_input field with its address.
    selected_wallet = app_data
    if selected_wallet in wallets:
        dpg.set_value("wallet_input", wallets[selected_wallet]["address"])
    else:
        dpg.set_value("wallet_input", "")

def check_balance(sender, app_data):
    """Check SOL or token balance for the specified wallet address."""
    if not enter():
        dpg.set_value("result_text", "Please check the checkbox to connect to the network")
        return
        
    wallet_address = dpg.get_value("wallet_input").strip()
    token_address = dpg.get_value("token_input").strip()
    
    # Validate wallet address input
    if not wallet_address:
        dpg.set_value("wallet_input", "Please Enter Wallet Address")
        dpg.set_value("result_text", "Wallet address is required")
        return

    url = "https://api.mainnet-beta.solana.com"
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        
        if token_address:
            # For token balance, call getTokenAccountsByOwner
            token_pubkey = Pubkey.from_string(token_address)
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getTokenAccountsByOwner",
                "params": [
                    str(wallet_pubkey),
                    {"mint": str(token_pubkey)},
                    {"encoding": "jsonParsed"}
                ]
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result_data = response.json()
            if "result" in result_data and result_data["result"]["value"]:
                token_amount = result_data["result"]["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                dpg.set_value("result_text", f"Token Balance: {token_amount}")
            else:
                dpg.set_value("result_text", "No token accounts found for this address")
        else:
            # For SOL balance, call getBalance
            payload = {
                "id": 1,
                "jsonrpc": "2.0",
                "method": "getBalance",
                "params": [str(wallet_pubkey)]
            }
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            
            result_data = response.json()
            if "result" in result_data:
                lamports = result_data["result"]["value"]
                sol_balance = lamports / 1e9
                dpg.set_value("result_text", f"SOL Balance: {sol_balance:.6f} SOL")
            else:
                dpg.set_value("result_text", "Failed to retrieve balance")
                
    except ValueError as e:
        dpg.set_value("result_text", f"Invalid address format: {str(e)}")
    except requests.RequestException as e:
        dpg.set_value("result_text", f"Network error: {str(e)}")
    except Exception as e:
        dpg.set_value("result_text", f"Error: {str(e)}")

def exit_app(sender, app_data):
    """Clean shutdown of the application."""
    try:
        dpg.destroy_context()
        dpg.stop_dearpygui()
    except Exception as e:
        print(f"Error during shutdown: {e}")

# ---------------------------
# Wallet Management Functions
# ---------------------------
def generate_wallet():
    """Generate a new Solana wallet with encrypted private key storage."""
    # Note: This function requires the Solana Keypair import to be enabled
    try:
        # Uncomment when solana.keypair is available
        # kp = Keypair()
        # address = str(kp.public_key)
        # private_key = base64.b64encode(kp.secret_key).decode("utf-8")
        # public_key = str(kp.public_key)
        
        # Placeholder implementation for demo
        address = "DemoGeneratedAddress" + str(len(wallets) + 1)
        private_key = "DemoPrivateKey" + str(len(wallets) + 1)
        public_key = address
        
        return {
            "address": address, 
            "private_key": encrypt_private_key(private_key), 
            "public_key": public_key
        }
    except Exception as e:
        print(f"Error generating wallet: {e}")
        return None

def generate_wallet_callback(sender, app_data):
    """Callback to generate a new wallet and update the UI."""
    new_wallet = generate_wallet()
    if new_wallet:
        wallet_name = f"wallet{len(wallets)+1}"
        wallets[wallet_name] = new_wallet
        dpg.set_value("wallet_input", new_wallet["address"])
        dpg.set_value("result_text", f"New Wallet Generated: {new_wallet['address']}")
        
        # Update the wallet combo box
        wallet_keys = list(wallets.keys())
        dpg.configure_item("wallet_combo", items=wallet_keys)
    else:
        dpg.set_value("result_text", "Failed to generate new wallet")

def import_wallet_callback(sender, app_data):
    """Import a wallet from a JSON file."""
    file_path = dpg.get_value("wallet_file_path").strip()
    
    if not file_path:
        dpg.set_value("result_text", "Please enter a file path")
        return
        
    if not os.path.exists(file_path):
        dpg.set_value("result_text", f"File does not exist: {file_path}")
        return
        
    try:
        with open(file_path, "r") as f:
            wallet_data = json.load(f)
            
        # Validate required fields
        required_fields = ["address", "private_key", "public_key"]
        for field in required_fields:
            if field not in wallet_data:
                dpg.set_value("result_text", f"Missing required field: {field}")
                return
        
        # Generate wallet name
        name = wallet_data.get("name", f"wallet{len(wallets)+1}")
        
        # Encrypt private key if not already encrypted
        if "private_key_encrypted" not in wallet_data:
            wallet_data["private_key"] = encrypt_private_key(wallet_data["private_key"])
            
        wallets[name] = {
            "address": wallet_data["address"],
            "private_key": wallet_data["private_key"],
            "public_key": wallet_data["public_key"]
        }
        
        dpg.set_value("wallet_input", wallet_data["address"])
        dpg.set_value("result_text", f"Imported wallet: {name} with address {wallet_data['address']}")
        
        # Update the wallet combo box
        wallet_keys = list(wallets.keys())
        dpg.configure_item("wallet_combo", items=wallet_keys)
        
    except json.JSONDecodeError:
        dpg.set_value("result_text", "Invalid JSON file format")
    except Exception as e:
        dpg.set_value("result_text", f"Error importing wallet: {str(e)}")

# ---------------------------
# Transaction Capabilities
# ---------------------------
def send_transaction(sender, app_data):
    """Send a Solana transaction (currently simulated)."""
    dest = dpg.get_value("destination_input").strip()
    amount = dpg.get_value("amount_input").strip()
    
    # Validate inputs
    if not dest or not amount:
        dpg.set_value("result_text", "Please enter destination address and amount.")
        return
        
    try:
        amount_float = float(amount)
        if amount_float <= 0:
            dpg.set_value("result_text", "Amount must be greater than 0.")
            return
    except ValueError:
        dpg.set_value("result_text", "Invalid amount format. Please enter a number.")
        return

    # Validate destination address format
    try:
        Pubkey.from_string(dest)
    except ValueError:
        dpg.set_value("result_text", "Invalid destination address format.")
        return

    # In production, a transaction would be built, signed with the wallet's private key (after decryption),
    # and sent via an RPC call. Here we simulate transaction sending.
    dpg.set_value("result_text", f"Transaction sent: {amount_float} SOL to {dest} (simulated)")
    print(f"Simulated transaction: {amount_float} SOL to {dest}")

# ---------------------------
# UI Setup and Window Layout
# ---------------------------
dpg.create_viewport(title='Solana Balance Checker', width=1280, height=720, decorated=True)

with dpg.window(tag="Primary_Window", label="Solana Networker", width=1280, height=720, no_title_bar=True, no_resize=True):
    with dpg.menu_bar():
        dpg.add_text(VERSION_, color=(0, 255, 0))
        with dpg.menu(label="File"):
            dpg.add_menu_item(label="Exit", callback=exit_app)
        with dpg.menu(label="Wallet"):
            dpg.add_menu_item(label="Copy address", callback=temp_callback)
            dpg.add_menu_item(label="List connected", callback=temp_callback)
            dpg.add_menu_item(label="Import Wallet", callback=import_wallet_callback)
            dpg.add_menu_item(label="Generate New Wallet", callback=generate_wallet_callback)
            dpg.add_menu_item(label="Export Wallet", callback=lambda: write_to_clipboard("copied!"))
        with dpg.menu(label="Network"):
            dpg.add_menu_item(label="Connect", callback=temp_callback)
            dpg.add_menu_item(label="Disconnect", callback=temp_callback)
            dpg.add_menu_item(label="Force refresh", callback=temp_callback)
    dpg.add_text(" * Always check you are sending to the correct address * ", color=(255, 0, 0))
    dpg.add_checkbox(label="Connect to network", default_value=False, callback=enter, tag="understand_checkbox")
    
    dpg.add_spacing(count=5)
    
    # Wallet Balance and Token Check UI
    dpg.add_text("Enter Wallet Address:")
    dpg.add_input_text(tag="wallet_input", default_value="", width=UI_WIDTH)
    
    dpg.add_text("Or select from your wallets:")
    wallet_keys = list(wallets.keys())
    dpg.add_combo(wallet_keys, tag="wallet_combo", width=UI_WIDTH, callback=wallet_combo_callback)
    
    dpg.add_text("Enter Token Address (optional):")
    dpg.add_input_text(tag="token_input", default_value="", width=UI_WIDTH)
    
    dpg.add_button(label="Check Balance", callback=check_balance, width=UI_WIDTH)
    
    dpg.add_text("Results will appear here", tag="result_text", color=(255, 0, 0))
    
    dpg.add_spacing(count=2)
    
    # Wallet Management: Import Wallet via File
    dpg.add_separator()
    dpg.add_text("Wallet Management")
    dpg.add_text("Enter Wallet File Path to Import:")
    dpg.add_input_text(tag="wallet_file_path", default_value="", width=UI_WIDTH)
    
    # Transaction UI
    dpg.add_separator()
    dpg.add_text("Send Transaction")
    dpg.add_text("Enter Destination Address:")
    dpg.add_input_text(tag="destination_input", default_value="", width=UI_WIDTH)
    dpg.add_text("Enter Amount (SOL):")
    dpg.add_input_text(tag="amount_input", default_value="", width=UI_WIDTH)
    dpg.add_button(label="Send Transaction", callback=send_transaction, width=UI_WIDTH)
    
    dpg.add_spacing(count=2)
    dpg.add_button(label="Exit", callback=exit_app, width=UI_WIDTH)
with dpg.window(tag="authenticationWindow", label="Authentication", width=400, height=500, no_title_bar=True, no_resize=True):
    with dpg.menu_bar():
        dpg.add_text("Solana Networker Authentication", color=(0, 255, 0))
    dpg.add_text("Enter your username:")
    dpg.add_input_text(tag="username", default_value="", width=UI_WIDTH)
    dpg.add_text("Enter your password:")
    dpg.add_input_text(tag="password", default_value="", password=True, width=UI_WIDTH)
    dpg.add_button(label="Login", callback=login, width=UI_WIDTH)
    dpg.add_button(label="Exit", callback=exit_app, width=UI_WIDTH)

dpg.setup_dearpygui()
dpg.show_viewport()

try:
    dpg.set_primary_window("Primary_Window", True)
except Exception as e:
    print(f"Note: Could not set primary window: {e}")

dpg.start_dearpygui()
dpg.destroy_context()

"""
Solana Network Interface Module

This module provides a GUI interface for interacting with the Solana blockchain,
including wallet management, balance checking, and transaction capabilities.
"""

import os
import subprocess
import json
import base64
import requests
import dearpygui.dearpygui as dpg
from solders.pubkey import Pubkey
from solana.rpc.api import Client
try:
    from solana.keypair import Keypair
except ImportError:
    # Fallback for different solana library versions
    try:
        from solders.keypair import Keypair
    except ImportError:
        print("Warning: Keypair import failed. Wallet generation may not work.")
        Keypair = None
from cryptography.fernet import Fernet

# Import security utilities
try:
    from utils.security import validate_solana_address, sanitize_input, validate_file_path, get_safe_env_var
except ImportError:
    # Fallback definitions if utils module not available
    def validate_solana_address(address: str) -> bool:
        return bool(address and len(address) >= 32 and len(address) <= 44)
    
    def sanitize_input(input_str: str, max_length: int = 1000) -> str:
        return str(input_str)[:max_length].strip() if input_str else ""
    
    def validate_file_path(file_path: str) -> bool:
        return bool(file_path and '..' not in file_path)
    
    def get_safe_env_var(var_name: str, default: str = "") -> str:
        return os.getenv(var_name, default)

VERSION_ = "Solana Networker (1a_2025)"

# ---------------------------
# Configuration Constants
# ---------------------------
KEY_FILE = "wallet_key.key"
DEFAULT_USERNAME = get_safe_env_var("SOLANA_USERNAME", "admin")
DEFAULT_PASSWORD = get_safe_env_var("SOLANA_PASSWORD", "admin")
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"
LAMPORTS_PER_SOL = 1e9

# ---------------------------
# Secure Key Management Setup
# ---------------------------
def setup_encryption_key():
    """
    Set up encryption key for secure wallet storage.
    
    Returns:
        Fernet: Encryption instance for wallet operations
    """
    if os.path.exists(KEY_FILE):
        with open(KEY_FILE, "rb") as f:
            encryption_key = f.read()
    else:
        encryption_key = Fernet.generate_key()
        with open(KEY_FILE, "wb") as f:
            f.write(encryption_key)
    return Fernet(encryption_key)

fernet = setup_encryption_key()

def encrypt_private_key(private_key: str) -> str:
    """
    Encrypt a private key for secure storage.
    
    Args:
        private_key (str): The private key to encrypt
        
    Returns:
        str: The encrypted private key
    """
    if not private_key:
        raise ValueError("Private key cannot be empty")
    return fernet.encrypt(private_key.encode()).decode()

def decrypt_private_key(encrypted_private_key: str) -> str:
    """
    Decrypt a private key for use.
    
    Args:
        encrypted_private_key (str): The encrypted private key
        
    Returns:
        str: The decrypted private key
    """
    if not encrypted_private_key:
        raise ValueError("Encrypted private key cannot be empty")
    return fernet.decrypt(encrypted_private_key.encode()).decode()

def authenticate_user():
    """
    Authenticate user credentials.
    
    Returns:
        bool: True if authentication successful, False otherwise
    """
    username = sanitize_input(dpg.get_value("username"), 50)
    password = sanitize_input(dpg.get_value("password"), 50)
    
    # In production, this should use proper authentication mechanism
    # Consider using environment variables or external auth service
    if username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD:
        dpg.delete_item("authenticationWindow")
        return True
    else:
        dpg.set_value("result_text", "Invalid username or password")
        return False

def login():
    """Legacy login function for backward compatibility."""
    authenticate_user()

def validate_wallet_address(address: str) -> bool:
    """
    Validate if a wallet address is in correct Solana format.
    
    Args:
        address (str): The wallet address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    # Use enhanced validation from security utils
    return validate_solana_address(sanitize_input(address, 50))

def validate_amount(amount_str: str) -> tuple[bool, float]:
    """
    Validate and convert amount string to float.
    
    Args:
        amount_str (str): The amount string to validate
        
    Returns:
        tuple[bool, float]: (is_valid, amount_value)
    """
    if not amount_str or not isinstance(amount_str, str):
        return False, 0.0
    
    try:
        amount = float(amount_str.strip())
        if amount <= 0:
            return False, 0.0
        return True, amount
    except (ValueError, TypeError):
        return False, 0.0

def safe_request(url: str, json_data: dict, headers: dict, timeout: int = 30) -> dict:
    """
    Make a safe HTTP request with proper error handling.
    
    Args:
        url (str): The URL to request
        json_data (dict): JSON data to send
        headers (dict): Request headers
        timeout (int): Request timeout in seconds
        
    Returns:
        dict: Response data or error information
    """
    try:
        response = requests.post(url, json=json_data, headers=headers, timeout=timeout)
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.exceptions.Timeout:
        return {"success": False, "error": "Request timed out"}
    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Network error: {str(e)}"}
    except json.JSONDecodeError:
        return {"success": False, "error": "Invalid JSON response"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}
# ---------------------------
# Wallets Dictionary (with encrypted private keys)
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
DEFAULT_WIDTH = 250
dpg.create_context()

def setup_fonts():
    """Set up application fonts with fallback options."""
    with dpg.font_registry():
        font_paths = [
            "/System/Library/Fonts/Supplemental/Optima.ttc",  # macOS
            "C:/Windows/Fonts/arial.ttf",  # Windows
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"  # Linux
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    default_font = dpg.add_font(font_path, 19)
                    dpg.bind_font(default_font)
                    break
                except Exception as e:
                    print(f"Could not load font {font_path}: {e}")
                    continue

setup_fonts()

# ---------------------------
# Utility Callback Functions
# ---------------------------
def temp_callback(sender, app_data):
    """Temporary callback function for placeholder functionality."""
    print(f"Button pressed: {sender}, data: {app_data}")

def write_to_clipboard(output: str):
    """
    Write output to system clipboard.
    
    Args:
        output (str): Text to copy to clipboard
    """
    try:
        # macOS
        process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
        process.communicate(output.encode('utf-8'))
    except FileNotFoundError:
        try:
            # Linux with xclip
            process = subprocess.Popen(['xclip', '-selection', 'clipboard'], stdin=subprocess.PIPE)
            process.communicate(output.encode('utf-8'))
        except FileNotFoundError:
            try:
                # Windows
                process = subprocess.Popen(['clip'], stdin=subprocess.PIPE, shell=True)
                process.communicate(output.encode('utf-8'))
            except Exception as e:
                print(f"Could not copy to clipboard: {e}")

def is_network_enabled() -> bool:
    """
    Check if network connection is enabled via checkbox.
    
    Returns:
        bool: True if network connection is enabled
    """
    try:
        return bool(dpg.get_value("understand_checkbox"))
    except Exception:
        return False

def wallet_combo_callback(sender, app_data):
    """
    Handle wallet selection from dropdown.
    
    Args:
        sender: The widget that triggered the callback
        app_data: The selected wallet name
    """
    selected_wallet = app_data
    if selected_wallet in wallets:
        dpg.set_value("wallet_input", wallets[selected_wallet]["address"])
    else:
        dpg.set_value("wallet_input", "")

def check_balance(sender, app_data):
    """
    Check wallet balance for SOL or specific token.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
    """
    if not is_network_enabled():
        dpg.set_value("result_text", "Please check the checkbox to connect to the network")
        return
        
    wallet_address = sanitize_input(dpg.get_value("wallet_input"), 50).strip()
    token_address = sanitize_input(dpg.get_value("token_input"), 50).strip()
    
    # Validate wallet address
    if not wallet_address:
        dpg.set_value("result_text", "Please enter a wallet address")
        return
        
    if not validate_wallet_address(wallet_address):
        dpg.set_value("result_text", "Invalid wallet address format")
        return
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json"
    }
    
    try:
        wallet_pubkey = Pubkey.from_string(wallet_address)
        
        if token_address:
            # Validate token address
            if not validate_wallet_address(token_address):
                dpg.set_value("result_text", "Invalid token address format")
                return
                
            token_pubkey = Pubkey.from_string(token_address)
            
            # Check token balance
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
            
            response = safe_request(SOLANA_RPC_URL, payload, headers)
            if not response["success"]:
                dpg.set_value("result_text", f"Error: {response['error']}")
                return
                
            result = response["data"]
            if not result.get("result", {}).get("value"):
                dpg.set_value("result_text", "No token accounts found for this token")
                return
                
            token_amount = result["result"]["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
            dpg.set_value("result_text", f"Token Balance: {token_amount}")
        else:
            # Check SOL balance
            payload = {
                "id": 1,
                "jsonrpc": "2.0", 
                "method": "getBalance",
                "params": [str(wallet_pubkey)]
            }
            
            response = safe_request(SOLANA_RPC_URL, payload, headers)
            if not response["success"]:
                dpg.set_value("result_text", f"Error: {response['error']}")
                return
                
            result = response["data"]
            lamports = result.get("result", {}).get("value", 0)
            sol_balance = lamports / LAMPORTS_PER_SOL
            dpg.set_value("result_text", f"SOL Balance: {sol_balance:.9f} SOL")
            
    except Exception as e:
        dpg.set_value("result_text", f"Error: {str(e)}")

def exit_app(sender, app_data):
    """
    Clean exit from the application.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
    """
    try:
        dpg.stop_dearpygui()
        dpg.destroy_context()
    except Exception as e:
        print(f"Error during exit: {e}")

# ---------------------------
# Wallet Management Functions
# ---------------------------
def generate_wallet() -> dict:
    """
    Generate a new Solana wallet.
    
    Returns:
        dict: Wallet information including address, encrypted private key, and public key
        
    Raises:
        RuntimeError: If Keypair is not available
    """
    if Keypair is None:
        raise RuntimeError("Keypair not available. Cannot generate wallet.")
        
    try:
        kp = Keypair()
        address = str(kp.public_key)
        # Encode the secret key in base64 for storage
        private_key = base64.b64encode(kp.secret_key).decode("utf-8")
        public_key = str(kp.public_key)
        return {
            "address": address, 
            "private_key": encrypt_private_key(private_key), 
            "public_key": public_key
        }
    except Exception as e:
        raise RuntimeError(f"Failed to generate wallet: {str(e)}")

def generate_wallet_callback(sender, app_data):
    """
    Callback to generate a new wallet and update UI.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
    """
    try:
        new_wallet = generate_wallet()
        wallet_name = f"wallet{len(wallets)+1}"
        wallets[wallet_name] = new_wallet
        dpg.set_value("wallet_input", new_wallet["address"])
        dpg.set_value("result_text", f"New Wallet Generated: {new_wallet['address']}")
    except Exception as e:
        dpg.set_value("result_text", f"Error generating wallet: {str(e)}")

def import_wallet_callback(sender, app_data):
    """
    Import a wallet from a JSON file.
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
    """
    file_path = sanitize_input(dpg.get_value("wallet_file_path"), 200).strip()
    
    if not file_path:
        dpg.set_value("result_text", "Please enter a file path")
        return
    
    # Validate file path for security
    if not validate_file_path(file_path):
        dpg.set_value("result_text", "Invalid or unsafe file path")
        return
        
    if not os.path.exists(file_path):
        dpg.set_value("result_text", f"File does not exist: {file_path}")
        return
        
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            wallet_data = json.load(f)
            
        # Validate required fields
        required_fields = ["address", "private_key", "public_key"]
        if not all(field in wallet_data for field in required_fields):
            dpg.set_value("result_text", f"Invalid wallet file. Required fields: {required_fields}")
            return
            
        # Sanitize and validate wallet address
        wallet_data["address"] = sanitize_input(wallet_data["address"], 50)
        if not validate_wallet_address(wallet_data["address"]):
            dpg.set_value("result_text", "Invalid wallet address in file")
            return
            
        # Encrypt private key if not already encrypted
        name = sanitize_input(wallet_data.get("name", f"wallet{len(wallets)+1}"), 50)
        if "private_key_encrypted" not in wallet_data:
            wallet_data["private_key"] = encrypt_private_key(wallet_data["private_key"])
            
        wallets[name] = wallet_data
        dpg.set_value("wallet_input", wallet_data["address"])
        dpg.set_value("result_text", f"Imported wallet: {name} with address {wallet_data['address']}")
        
    except json.JSONDecodeError:
        dpg.set_value("result_text", "Invalid JSON file format")
    except Exception as e:
        dpg.set_value("result_text", f"Error importing wallet: {str(e)}")

# ---------------------------
# Transaction Capabilities
# ---------------------------
def send_transaction(sender, app_data):
    """
    Send a SOL transaction (simulated for security).
    
    Args:
        sender: The widget that triggered the callback
        app_data: Additional data from the callback
    """
    dest_address = sanitize_input(dpg.get_value("destination_input"), 50).strip()
    amount_str = sanitize_input(dpg.get_value("amount_input"), 20).strip()
    
    if not dest_address or not amount_str:
        dpg.set_value("result_text", "Please enter destination address and amount.")
        return
        
    # Validate destination address
    if not validate_wallet_address(dest_address):
        dpg.set_value("result_text", "Invalid destination address format")
        return
        
    # Validate amount
    is_valid, amount = validate_amount(amount_str)
    if not is_valid:
        dpg.set_value("result_text", "Invalid amount format. Must be a positive number.")
        return

    # In production, this would:
    # 1. Build the transaction
    # 2. Sign with the wallet's private key (after decryption)
    # 3. Send via RPC call
    # For security, we simulate the transaction here
    dpg.set_value("result_text", f"Transaction sent: {amount} SOL to {dest_address} (simulated)")
    print(f"Simulated transaction: {amount} SOL to {dest_address}")

# ---------------------------
# UI Setup and Window Layout
# ---------------------------
def create_main_window():
    """Create and configure the main application window."""
    dpg.create_viewport(title='Solana Balance Checker', width=1280, height=720, decorated=True)

    with dpg.window(tag="Primary_Window", label="Solana Networker", width=1280, height=720, no_title_bar=True, no_resize=True):
        create_menu_bar()
        create_main_content()

def create_menu_bar():
    """Create the application menu bar."""
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

def create_main_content():
    """Create the main content area of the application."""
    dpg.add_text(" * Always check you are sending to the correct address * ", color=(255, 0, 0))
    dpg.add_checkbox(label="Connect to network", default_value=False, tag="understand_checkbox")
    
    dpg.add_spacing(count=5)
    
    create_balance_section()
    create_wallet_management_section()
    create_transaction_section()
    
    dpg.add_spacing(count=2)
    dpg.add_button(label="Exit", callback=exit_app, width=DEFAULT_WIDTH)

def create_balance_section():
    """Create the balance checking section."""
    dpg.add_text("Enter Wallet Address:")
    dpg.add_input_text(tag="wallet_input", default_value="", width=DEFAULT_WIDTH)
    
    dpg.add_text("Or select from your wallets:")
    wallet_keys = list(wallets.keys())
    dpg.add_combo(wallet_keys, tag="wallet_combo", width=DEFAULT_WIDTH, callback=wallet_combo_callback)
    
    dpg.add_text("Enter Token Address (optional):")
    dpg.add_input_text(tag="token_input", default_value="", width=DEFAULT_WIDTH)
    
    dpg.add_button(label="Check Balance", callback=check_balance, width=DEFAULT_WIDTH)
    
    dpg.add_text("Results will appear here", tag="result_text", color=(255, 0, 0))
    dpg.add_spacing(count=2)

def create_wallet_management_section():
    """Create the wallet management section."""
    dpg.add_separator()
    dpg.add_text("Wallet Management")
    dpg.add_text("Enter Wallet File Path to Import:")
    dpg.add_input_text(tag="wallet_file_path", default_value="", width=DEFAULT_WIDTH)

def create_transaction_section():
    """Create the transaction section."""
    dpg.add_separator()
    dpg.add_text("Send Transaction")
    dpg.add_text("Enter Destination Address:")
    dpg.add_input_text(tag="destination_input", default_value="", width=DEFAULT_WIDTH)
    dpg.add_text("Enter Amount (SOL):")
    dpg.add_input_text(tag="amount_input", default_value="", width=DEFAULT_WIDTH)
    dpg.add_button(label="Send Transaction", callback=send_transaction, width=DEFAULT_WIDTH)

def create_auth_window():
    """Create the authentication window."""
    with dpg.window(tag="authenticationWindow", label="Authentication", width=400, height=500, no_title_bar=True, no_resize=True):
        with dpg.menu_bar():
            dpg.add_text("Solana Networker Authentication", color=(0, 255, 0))
        dpg.add_text("Enter your username:")
        dpg.add_input_text(tag="username", default_value="", width=DEFAULT_WIDTH)
        dpg.add_text("Enter your password:")
        dpg.add_input_text(tag="password", default_value="", password=True, width=DEFAULT_WIDTH)
        dpg.add_button(label="Login", callback=login, width=DEFAULT_WIDTH)
        dpg.add_button(label="Exit", callback=exit_app, width=DEFAULT_WIDTH)

# Initialize the application
create_main_window()
create_auth_window()

def main():
    """Main application entry point."""
    try:
        dpg.setup_dearpygui()
        dpg.show_viewport()

        try:
            dpg.set_primary_window("Primary_Window", True)
        except Exception as e:
            print(f"Note: Could not set primary window: {e}")

        dpg.start_dearpygui()
        
    except Exception as e:
        print(f"Error running application: {e}")
    finally:
        dpg.destroy_context()

if __name__ == "__main__":
    main()

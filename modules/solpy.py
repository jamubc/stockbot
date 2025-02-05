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
    return fernet.encrypt(pk.encode()).decode()

def decrypt_private_key(encrypted_pk: str) -> str:
    return fernet.decrypt(encrypted_pk.encode()).decode()

def login():
    username = dpg.get_value("username")
    password = dpg.get_value("password")
    if username == "admin" and password == "admin":
        dpg.delete_item("authenticationWindow")
    else:
        dpg.set_value("result_text", "Invalid username or password")

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
width_ = 250
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
def tempCallback(sender, app_data):
    print("Button Pressed")

def write_to_clipboard(output):
    process = subprocess.Popen('pbcopy', env={'LANG': 'en_US.UTF-8'}, stdin=subprocess.PIPE)
    process.communicate(output.encode('utf-8'))

def enter():
    # Returns True if the "Connect to network" checkbox is checked.
    understand = dpg.get_value("understand_checkbox")
    return bool(understand)

def wallet_combo_callback(sender, app_data):
    # When a wallet is selected from the dropdown, update the wallet_input field with its address.
    selected_wallet = app_data
    if selected_wallet in wallets:
        dpg.set_value("wallet_input", wallets[selected_wallet]["address"])
    else:
        dpg.set_value("wallet_input", "")

def check_balance(sender, app_data):
    if not enter():
        dpg.set_value("result_text", "Please check the checkbox to connect to the network")
        
    else:
        wallet_address = dpg.get_value("wallet_input").strip()
        token_address = dpg.get_value("token_input").strip()
        
        # If wallet address is empty, use a default example address and update the UI
        if not wallet_address:
            dpg.set_value("wallet_input", "Please Enter Wallet Address")

        url = "https://api.mainnet-beta.solana.com"
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        try:
            wallet_pubkey = Pubkey.from_string(wallet_address)
            token_pubkey = Pubkey.from_string(token_address) if token_address else None

            if token_pubkey:
                # For token balance, call getTokenAccountsByOwner
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
                response = requests.post(url, json=payload, headers=headers)
                token_amount = response.json()["result"]["value"][0]["account"]["data"]["parsed"]["info"]["tokenAmount"]["uiAmount"]
                dpg.set_value("result_text", f"Token Balance: {token_amount}")
            else:
                # For SOL balance, call getBalance
                payload = {
                    "id": 1,
                    "jsonrpc": "2.0",
                    "method": "getBalance",
                    "params": [str(wallet_pubkey)]
                }
                response = requests.post(url, json=payload, headers=headers)
                lamports = response.json()["result"]["value"]
                dpg.set_value("result_text", f"SOL Balance: {lamports/1e9} SOL")
        except Exception as e:
            dpg.set_value("result_text", f"Error: {str(e)}")

def exit_app(sender, app_data):
    dpg.destroy_context()
    dpg.stop_dearpygui()

# ---------------------------
# Wallet Management Functions
# ---------------------------
def generate_wallet():
    kp = Keypair()
    address = str(kp.public_key)
    # Encode the secret key in base64 for storage
    private_key = base64.b64encode(kp.secret_key).decode("utf-8")
    public_key = str(kp.public_key)
    return {"address": address, "private_key": encrypt_private_key(private_key), "public_key": public_key}

def generate_wallet_callback(sender, app_data):
    new_wallet = generate_wallet()
    wallet_name = f"wallet{len(wallets)+1}"
    wallets[wallet_name] = new_wallet
    dpg.set_value("wallet_input", new_wallet["address"])
    dpg.set_value("result_text", f"New Wallet Generated: {new_wallet['address']}")

def import_wallet_callback(sender, app_data):
    file_path = dpg.get_value("wallet_file_path").strip()
    if not os.path.exists(file_path):
        dpg.set_value("result_text", f"File does not exist: {file_path}")
        return
    try:
        with open(file_path, "r") as f:
            wallet_data = json.load(f)
        # Expecting wallet_data to have keys: name, address, private_key, public_key
        name = wallet_data.get("name", f"wallet{len(wallets)+1}")
        if "private_key_encrypted" not in wallet_data:
            wallet_data["private_key"] = encrypt_private_key(wallet_data["private_key"])
        wallets[name] = wallet_data
        dpg.set_value("wallet_input", wallet_data["address"])
        dpg.set_value("result_text", f"Imported wallet: {name} with address {wallet_data['address']}")
    except Exception as e:
        dpg.set_value("result_text", f"Error importing wallet: {str(e)}")

# ---------------------------
# Transaction Capabilities
# ---------------------------
def send_transaction(sender, app_data):
    dest = dpg.get_value("destination_input").strip()
    amount = dpg.get_value("amount_input").strip()
    if not dest or not amount:
        dpg.set_value("result_text", "Please enter destination address and amount.")
        return
    try:
        amount_float = float(amount)
    except:
        dpg.set_value("result_text", "Invalid amount format.")
        return

    # In production, a transaction would be built, signed with the wallet's private key (after decryption),
    # and sent via an RPC call. Here we simulate transaction sending.
    dpg.set_value("result_text", f"Transaction sent: {amount_float} SOL to {dest} (simulated)")

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
            dpg.add_menu_item(label="Copy address", callback=tempCallback)
            dpg.add_menu_item(label="List connected", callback=tempCallback)
            dpg.add_menu_item(label="Import Wallet", callback=import_wallet_callback)
            dpg.add_menu_item(label="Generate New Wallet", callback=generate_wallet_callback)
            dpg.add_menu_item(label="Export Wallet", callback=lambda: write_to_clipboard("copied!"))
        with dpg.menu(label="Network"):
            dpg.add_menu_item(label="Connect", callback=tempCallback)
            dpg.add_menu_item(label="Disconnect", callback=tempCallback)
            dpg.add_menu_item(label="Force refresh", callback=tempCallback)
    dpg.add_text(" * Always check you are sending to the correct address * ", color=(255, 0, 0))
    dpg.add_checkbox(label="Connect to network", default_value=False, callback=enter, tag="understand_checkbox")
    
    dpg.add_spacing(count=5)
    
    # Wallet Balance and Token Check UI
    dpg.add_text("Enter Wallet Address:")
    dpg.add_input_text(tag="wallet_input", default_value="", width=width_)
    
    dpg.add_text("Or select from your wallets:")
    wallet_keys = list(wallets.keys())
    dpg.add_combo(wallet_keys, tag="wallet_combo", width=width_, callback=wallet_combo_callback)
    
    dpg.add_text("Enter Token Address (optional):")
    dpg.add_input_text(tag="token_input", default_value="", width=width_)
    
    dpg.add_button(label="Check Balance", callback=check_balance, width=width_)
    
    dpg.add_text("Results will appear here", tag="result_text", color=(255, 0, 0))
    
    dpg.add_spacing(count=2)
    
    # Wallet Management: Import Wallet via File
    dpg.add_separator()
    dpg.add_text("Wallet Management")
    dpg.add_text("Enter Wallet File Path to Import:")
    dpg.add_input_text(tag="wallet_file_path", default_value="", width=width_)
    
    # Transaction UI
    dpg.add_separator()
    dpg.add_text("Send Transaction")
    dpg.add_text("Enter Destination Address:")
    dpg.add_input_text(tag="destination_input", default_value="", width=width_)
    dpg.add_text("Enter Amount (SOL):")
    dpg.add_input_text(tag="amount_input", default_value="", width=width_)
    dpg.add_button(label="Send Transaction", callback=send_transaction, width=width_)
    
    dpg.add_spacing(count=2)
    dpg.add_button(label="Exit", callback=exit_app, width=width_)
with dpg.window(tag="authenticationWindow", label="Authentication", width=400, height=500, no_title_bar=True, no_resize=True):
    with dpg.menu_bar():
        dpg.add_text("Solana Networker Authentication", color=(0, 255, 0))
    dpg.add_text("Enter your username:")
    dpg.add_input_text(tag="username", default_value="", width=width_)
    dpg.add_text("Enter your password:")
    dpg.add_input_text(tag="password", default_value="", width=width_)
    dpg.add_button(label="Login", callback=login, width=width_)
    dpg.add_button(label="Exit", callback=exit_app, width=width_)

dpg.setup_dearpygui()
dpg.show_viewport()

try:
    dpg.set_primary_window("Primary_Window", True)
except Exception as e:
    print(f"Note: Could not set primary window: {e}")

dpg.start_dearpygui()
dpg.destroy_context()

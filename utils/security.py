"""
Security utilities and constants for the stockbot application.
"""

import os
import re
from typing import Optional

# Security constants
MIN_PASSWORD_LENGTH = 8
MAX_INPUT_LENGTH = 1000
SOLANA_ADDRESS_LENGTH_RANGE = (32, 44)

def validate_solana_address(address: str) -> bool:
    """
    Validate Solana address format more thoroughly.
    
    Args:
        address (str): The address to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    if not address or not isinstance(address, str):
        return False
    
    # Remove whitespace
    address = address.strip()
    
    # Check length
    if len(address) < SOLANA_ADDRESS_LENGTH_RANGE[0] or len(address) > SOLANA_ADDRESS_LENGTH_RANGE[1]:
        return False
    
    # Check for valid base58 characters (no 0, O, I, l)
    valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    if not all(c in valid_chars for c in address):
        return False
    
    return True

def sanitize_input(input_str: str, max_length: int = MAX_INPUT_LENGTH) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        input_str (str): The input to sanitize
        max_length (int): Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not input_str:
        return ""
    
    # Convert to string if not already
    input_str = str(input_str)
    
    # Limit length
    input_str = input_str[:max_length]
    
    # Remove control characters except newline and tab
    input_str = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', input_str)
    
    return input_str.strip()

def validate_file_path(file_path: str) -> bool:
    """
    Validate file path for security (prevent directory traversal).
    
    Args:
        file_path (str): The file path to validate
        
    Returns:
        bool: True if safe, False otherwise
    """
    if not file_path or not isinstance(file_path, str):
        return False
    
    # Normalize path
    normalized = os.path.normpath(file_path)
    
    # Check for directory traversal attempts
    if '..' in normalized or normalized.startswith('/'):
        return False
    
    # Check for suspicious patterns
    suspicious_patterns = ['../', '..\\', '/etc/', '/proc/', '/sys/', 'C:\\Windows\\']
    if any(pattern in file_path for pattern in suspicious_patterns):
        return False
    
    return True

def get_safe_env_var(var_name: str, default: str = "") -> str:
    """
    Safely get environment variable with sanitization.
    
    Args:
        var_name (str): Environment variable name
        default (str): Default value if not found
        
    Returns:
        str: Sanitized environment variable value
    """
    value = os.getenv(var_name, default)
    return sanitize_input(value, 100)  # Limit env vars to 100 chars
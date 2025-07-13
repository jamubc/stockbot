# Stockbot - Solana Network Tools

A Python GUI application suite for Solana blockchain interaction, featuring wallet management, balance checking, and network tools.

## Features

### Launcher (`launcher.py`)
- Automatic configuration updates from GitHub
- Dependency management and installation
- Module downloading and verification
- GUI interface for launching tools

### Solana Networker (`modules/solpy.py`)
- Wallet management (import, export, generate)
- SOL and SPL token balance checking
- Transaction simulation
- Secure encrypted key storage
- User-friendly GUI interface

## Requirements

- Python 3.7+
- See `requirements.txt` for Python package dependencies

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/jamubc/stockbot.git
   cd stockbot
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the launcher:
   ```bash
   python launcher.py
   ```

## Usage

### Using the Launcher
1. Run `python launcher.py`
2. Use the "Wizard" tab to check and install dependencies
3. Use the "Launcher" tab to start available tools

### Using Solana Networker
1. Launch through the main launcher or run directly: `python modules/solpy.py`
2. Enter credentials to access the application
3. Use the interface to:
   - Check wallet balances
   - Import/export wallets
   - Send transactions (simulated)

## Security Notes

- Private keys are encrypted using Fernet encryption
- Wallet key files are automatically excluded from version control
- This is a demonstration application - use proper security practices for production

## Configuration

The application uses `config.json` for configuration management. This file is automatically updated from the remote repository when using the launcher.

## File Structure

```
stockbot/
├── launcher.py          # Main launcher application
├── modules/
│   └── solpy.py        # Solana networking tool
├── config.json         # Configuration file
├── requirements.txt    # Python dependencies
└── README.md          # This file
```

## Development

The codebase follows Python best practices with:
- Type hints where applicable
- Comprehensive error handling
- Clear documentation and comments
- Consistent naming conventions

## License

This project is provided as-is for educational and demonstration purposes.
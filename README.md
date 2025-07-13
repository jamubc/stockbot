# Stockbot

A Python-based application suite for interacting with the Solana blockchain, featuring a GUI launcher and wallet management capabilities.

## Features

- **Launcher Application**: Main entry point with module management and dependency checking
- **Solana Network Interface**: GUI application for wallet management, balance checking, and transactions
- **Secure Wallet Storage**: Encrypted private key storage with local key management
- **Module Wizard**: Automated dependency installation and verification

## Requirements

- Python 3.9 or higher
- Dependencies listed in `requirements.txt`

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

### Launcher Application

The launcher provides two main tabs:

- **Launcher**: Launch individual applications
- **Wizard**: Check and install required modules and dependencies

### Solana Network Interface

The Solana module (`modules/solpy.py`) provides:

- Wallet balance checking for SOL and SPL tokens
- Wallet generation and import functionality
- Secure private key management with encryption
- Transaction capabilities (simulated for security)

## Security Features

- Private keys are encrypted using the `cryptography` library
- Authentication system for application access
- Input validation for wallet addresses and amounts
- Network request timeout and error handling

## Configuration

The application uses a `config.json` file that can be automatically downloaded from the repository. The configuration includes:

- Version information
- Required dependencies
- Python module requirements

## Environment Variables

- `SOLANA_USERNAME`: Override default authentication username
- `SOLANA_PASSWORD`: Override default authentication password

## Testing

You can verify the installation and functionality by running the test script:

```bash
python test_stockbot.py
```

This will check:
- File structure integrity
- Configuration validity  
- Module imports (where possible)
- Security function functionality

## Development

For development work, install additional dependencies:

```bash
pip install -r requirements-dev.txt
```

### Code Structure

- `launcher.py`: Main launcher application
- `modules/solpy.py`: Solana network interface
- `config.json`: Application configuration
- `requirements.txt`: Python dependencies

### Code Quality

The codebase follows Python best practices:

- Comprehensive error handling
- Input validation
- Secure credential management
- Modular function design
- Comprehensive documentation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the existing code style
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub.
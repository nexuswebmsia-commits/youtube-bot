import os
from auth_utils import get_authenticated_service

if __name__ == "__main__":
    print("--- YouTube MCP Server Authentication Setup ---")
    print("This script will guide you through authenticating with the YouTube Data API v3.")
    print("Please ensure your OAuth 2.0 client secrets file (e.g., client_secret.json) is in this directory.")
    input("Press Enter to continue...")
    try:
        get_authenticated_service()
        print("Authentication successful! A 'token.pickle' file has been created.")
        print("You can now run the MCP server.")
    except Exception as e:
        print(f"Authentication failed: {e}")

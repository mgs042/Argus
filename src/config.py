import os
import json
# Path to your JSON configuration file
CONFIG_FILE = 'config.json'

def set_env_vars():
    try:
        # Load the JSON file
        with open(CONFIG_FILE, 'r') as file:
            config = json.load(file)

        # Set each key-value pair as an environment variable
        for key, value in config.items():
            os.environ[key] = str(value)  # Convert value to string if not already

        print("Environment variables set successfully.")

    except FileNotFoundError:
        print(f"Configuration file '{CONFIG_FILE}' not found.")
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
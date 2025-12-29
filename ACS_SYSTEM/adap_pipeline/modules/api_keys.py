#!/usr/bin/env python3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.expanduser("~/adaptive_vault/.env"))

def get_apilayer_key():
    key = os.getenv("APILAYER_KEY")
    if not key:
        raise EnvironmentError("Missing APILAYER_KEY in .env")
    return key

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    GOOGLE_DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID', '')
    
    REQUEST_DELAY = float(os.getenv('REQUEST_DELAY', '2.0'))
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
    
    USER_AGENT = os.getenv(
        'USER_AGENT',
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    )
    
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', 'output')
    
    DEAL_TAGS = {
        (1, 5): 'Deals: 1-5',
        (6, 10): 'Deals: 6-10',
        (11, 20): 'Deals: 11-20',
        (21, 30): 'Deals: 21-30',
        (31, float('inf')): 'Deals: 30+'
    }


config = Config()

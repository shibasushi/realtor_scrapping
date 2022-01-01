import logging
from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]


class GoogleSheetsManager:
    def __init__(self, credentials_file: Optional[str] = None):
        self.credentials_file = credentials_file or config.GOOGLE_CREDENTIALS_FILE
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the Google Sheets client with service account credentials."""
        try:
            credentials = Credentials.from_service_account_file(
                self.credentials_file,
                scopes=SCOPES
            )
            self.client = gspread.authorize(credentials)
            logger.info("Google Sheets client initialized successfully")
        except FileNotFoundError:
            logger.warning(
                f"Credentials file not found: {self.credentials_file}. "
                "Google Sheets integration will be disabled."
            )
            self.client = None
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Google Sheets integration is available."""
        return self.client is not None
    
    def create_spreadsheet_for_zip(
        self, 
        zip_code: str, 
        agents: list[dict],
        folder_id: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new spreadsheet for a zip code with agent data.
        
        Returns the spreadsheet URL if successful, None otherwise.
        """
        if not self.is_available():
            logger.warning("Google Sheets client not available, skipping sheet creation")
            return None
        
        folder_id = folder_id or config.GOOGLE_DRIVE_FOLDER_ID
        spreadsheet_name = f"Realtor_{zip_code}"
        
        try:
            existing = self._find_existing_spreadsheet(spreadsheet_name, folder_id)
            if existing:
                logger.info(f"Updating existing spreadsheet: {spreadsheet_name}")
                spreadsheet = existing
                worksheet = spreadsheet.sheet1
                worksheet.clear()
            else:
                logger.info(f"Creating new spreadsheet: {spreadsheet_name}")
                spreadsheet = self.client.create(spreadsheet_name)
                worksheet = spreadsheet.sheet1
                
                if folder_id:
                    self._move_to_folder(spreadsheet.id, folder_id)
            
            self._populate_worksheet(worksheet, agents)
            self._format_worksheet(worksheet, len(agents))
            
            logger.info(f"Spreadsheet created/updated: {spreadsheet.url}")
            return spreadsheet.url
            
        except Exception as e:
            logger.error(f"Error creating spreadsheet for zip {zip_code}: {e}")
            return None
    
    def _find_existing_spreadsheet(
        self, 
        name: str, 
        folder_id: Optional[str]
    ) -> Optional[gspread.Spreadsheet]:
        """Find an existing spreadsheet by name in the specified folder."""
        try:
            spreadsheets = self.client.list_spreadsheet_files()
            for ss in spreadsheets:
                if ss['name'] == name:
                    return self.client.open_by_key(ss['id'])
        except Exception as e:
            logger.debug(f"Could not search for existing spreadsheet: {e}")
        return None
    
    def _move_to_folder(self, file_id: str, folder_id: str):
        """Move a file to a specific Google Drive folder."""
        try:
            drive_service = self.client.http_client.session
            
            url = f'https://www.googleapis.com/drive/v3/files/{file_id}'
            params = {
                'addParents': folder_id,
                'removeParents': 'root',
                'fields': 'id, parents'
            }
            
            response = drive_service.patch(url, params=params)
            
            if response.status_code == 200:
                logger.info(f"Moved file {file_id} to folder {folder_id}")
            else:
                logger.warning(f"Could not move file to folder: {response.text}")
                
        except Exception as e:
            logger.warning(f"Could not move file to folder: {e}")
    
    def _populate_worksheet(self, worksheet: gspread.Worksheet, agents: list[dict]):
        """Populate the worksheet with agent data."""
        headers = [
            'Name',
            'Phone',
            'Email',
            'Brokerage',
            'Years Experience',
            'Recent Sales',
            'Active Listings',
            'Rating',
            'Specialties',
            'Profile URL'
        ]
        
        rows = [headers]
        
        for agent in agents:
            row = [
                agent.get('name', ''),
                agent.get('phone', '') or '',
                agent.get('email', '') or '',
                agent.get('brokerage', '') or '',
                str(agent.get('years_experience', '')) if agent.get('years_experience') else '',
                str(agent.get('recent_sales_count', 0)),
                str(agent.get('active_listings', 0)),
                str(agent.get('rating', '')) if agent.get('rating') else '',
                agent.get('specialties', '') or '',
                agent.get('profile_url', '') or ''
            ]
            rows.append(row)
        
        if rows:
            worksheet.update(rows, 'A1')
            logger.info(f"Added {len(rows) - 1} agents to worksheet")
    
    def _format_worksheet(self, worksheet: gspread.Worksheet, num_agents: int):
        """Apply formatting to the worksheet."""
        try:
            worksheet.format('A1:J1', {
                'textFormat': {'bold': True},
                'backgroundColor': {'red': 0.2, 'green': 0.4, 'blue': 0.8},
                'horizontalAlignment': 'CENTER'
            })
            
            worksheet.freeze(rows=1)
            
            column_widths = [
                ('A', 200),  # Name
                ('B', 150),  # Phone
                ('C', 200),  # Email
                ('D', 200),  # Brokerage
                ('E', 120),  # Years Experience
                ('F', 100),  # Recent Sales
                ('G', 120),  # Active Listings
                ('H', 80),   # Rating
                ('I', 200),  # Specialties
                ('J', 300),  # Profile URL
            ]
            
            requests = []
            for col_letter, width in column_widths:
                col_index = ord(col_letter) - ord('A')
                requests.append({
                    'updateDimensionProperties': {
                        'range': {
                            'sheetId': worksheet.id,
                            'dimension': 'COLUMNS',
                            'startIndex': col_index,
                            'endIndex': col_index + 1
                        },
                        'properties': {'pixelSize': width},
                        'fields': 'pixelSize'
                    }
                })
            
            if requests:
                worksheet.spreadsheet.batch_update({'requests': requests})
            
            logger.info("Worksheet formatting applied")
            
        except Exception as e:
            logger.warning(f"Could not apply full formatting: {e}")


def create_sheet_for_zip(zip_code: str, agents: list[dict]) -> Optional[str]:
    """Main entry point for creating a Google Sheet for a zip code."""
    manager = GoogleSheetsManager()
    return manager.create_spreadsheet_for_zip(zip_code, agents)


if __name__ == '__main__':
    test_agents = [
        {
            'name': 'John Smith',
            'phone': '555-123-4567',
            'email': 'john@example.com',
            'brokerage': 'ABC Realty',
            'years_experience': 10,
            'recent_sales_count': 25,
            'active_listings': 5,
            'rating': 4.8,
            'specialties': 'Luxury Homes, First-Time Buyers',
            'profile_url': 'https://example.com/agent/john'
        }
    ]
    
    print("Testing Google Sheets integration...")
    manager = GoogleSheetsManager()
    
    if manager.is_available():
        url = manager.create_spreadsheet_for_zip('00000', test_agents)
        if url:
            print(f"Created test spreadsheet: {url}")
        else:
            print("Failed to create spreadsheet")
    else:
        print("Google Sheets not configured (credentials.json not found)")

# Realtor.com Agent Scraper

A Flask-based tool for scraping real estate agent data from Realtor.com by zip code. Generates GHL-ready CSV exports and Google Sheets reports.

## Features

- **Web Interface**: Enter zip codes through a clean browser UI
- **NEXT_DATA Parsing**: Extracts agent data from Realtor.com's embedded JSON
- **Auto-Tagging**: Automatically generates GHL tags based on:
  - Deal volume (1-5, 6-10, 11-20, 21-30, 30+)
  - Zip code
  - Phone availability
  - Email availability
  - Experience level
  - Rating tier
- **Google Sheets Integration**: Creates individual spreadsheets per zip code (e.g., `Realtor_90210`)
- **GHL-Ready CSV**: Export format compatible with GoHighLevel import
- **Sorted Results**: Agents sorted by recent sales count (highest first)

## Data Extracted

| Field | Description |
|-------|-------------|
| Name | Agent's full name |
| Phone | Primary phone number |
| Email | Email address (if public) |
| Brokerage | Agency/company name |
| Years Experience | Years in the industry |
| Recent Sales | Number of recent sales |
| Active Listings | Current active listings |
| Rating | Agent rating (if available) |
| Specialties | Areas of specialization |
| Profile URL | Link to Realtor.com profile |

## Installation

### 1. Clone and Setup

```bash
cd realtor_scrapping
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example environment file:

```bash
copy .env.example .env    # Windows
cp .env.example .env      # macOS/Linux
```

Edit `.env` with your settings:

```env
SECRET_KEY=your-secure-secret-key
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
REQUEST_DELAY=2.0
```

### 3. Google Sheets Setup (Optional)

To enable Google Sheets integration:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable the **Google Sheets API** and **Google Drive API**
4. Create a Service Account:
   - Go to "IAM & Admin" → "Service Accounts"
   - Create a new service account
   - Download the JSON key file
5. Rename the key file to `credentials.json` and place in project root
6. Share your target Google Drive folder with the service account email

## Usage

### Web Interface

```bash
python app.py
```

Open http://localhost:5000 in your browser.

1. Enter zip codes (space or comma separated)
2. Select output options (CSV and/or Google Sheets)
3. Click "Start Scraping"
4. Download results or access Google Sheets

### Command Line

```bash
# Test scraper directly
python scraper.py 90210

# Test CSV export
python csv_export.py

# Test Google Sheets (requires credentials.json)
python google_sheets.py
```

### API

```bash
# POST /api/scrape
curl -X POST http://localhost:5000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"zip_codes": ["90210", "10001"], "create_csv": true}'
```

## GHL Import

The generated CSV includes these columns mapped for GoHighLevel:

| CSV Column | GHL Field |
|------------|-----------|
| firstName | First Name |
| lastName | Last Name |
| email | Email |
| phone | Phone (formatted +1XXXXXXXXXX) |
| companyName | Company |
| tags | Tags (comma-separated) |
| customField.* | Custom Fields |

### Auto-Generated Tags

Each contact receives automatic tags:

- `Zip: 90210` - Source zip code
- `Deals: 21-30` - Deal volume tier
- `Has Phone` / `No Phone` - Phone availability
- `Has Email` / `No Email` - Email availability
- `Exp: 10+ Years` - Experience tier
- `Rating: Top Rated` - For 4.5+ ratings
- `Source: Realtor.com` - Data source

## Project Structure

```
realtor_scrapping/
├── app.py              # Flask application
├── scraper.py          # Realtor.com scraper
├── google_sheets.py    # Google Sheets integration
├── csv_export.py       # GHL CSV generator
├── config.py           # Configuration
├── requirements.txt    # Dependencies
├── .env.example        # Environment template
├── credentials.json    # Google API credentials (not in repo)
├── templates/
│   ├── base.html       # Base template
│   ├── index.html      # Home page
│   ├── results.html    # Results page
│   └── preview.html    # Data preview
└── output/             # Generated CSV files
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| SECRET_KEY | dev-key | Flask secret key |
| GOOGLE_CREDENTIALS_FILE | credentials.json | Path to Google API credentials |
| GOOGLE_DRIVE_FOLDER_ID | (empty) | Target Drive folder ID |
| REQUEST_DELAY | 2.0 | Seconds between requests |
| MAX_RETRIES | 3 | Retry attempts on failure |
| REQUEST_TIMEOUT | 30 | Request timeout in seconds |
| OUTPUT_DIR | output | CSV output directory |

## Troubleshooting

### No agents found

The scraper targets Realtor.com's `__NEXT_DATA__` JSON structure. If the site structure changes:

1. Check if the URL format changed: `realtor.com/realestateagents/{zip}`
2. Inspect the page source for `__NEXT_DATA__` script tag
3. Update `_extract_agents_from_next_data()` in `scraper.py`

### Google Sheets not working

1. Verify `credentials.json` exists and is valid
2. Check the service account email has access to the target folder
3. Ensure both Sheets API and Drive API are enabled

### Rate limiting

If you encounter rate limiting:

1. Increase `REQUEST_DELAY` in `.env`
2. Use fewer zip codes per batch
3. Consider adding proxy rotation (not included)

## Legal Notice

This tool is for educational purposes. Respect Realtor.com's Terms of Service and robots.txt. Use responsibly and at your own risk.

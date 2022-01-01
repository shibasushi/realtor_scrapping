import os
import logging
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for

from config import config
from scraper import scrape_agents
from google_sheets import create_sheet_for_zip, GoogleSheetsManager
from csv_export import export_agents_to_ghl_csv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = config.SECRET_KEY

os.makedirs(config.OUTPUT_DIR, exist_ok=True)

scrape_results = {}


@app.route('/')
def index():
    """Render the main page with zip code input form."""
    sheets_available = GoogleSheetsManager().is_available()
    return render_template('index.html', sheets_available=sheets_available)


@app.route('/scrape', methods=['POST'])
def scrape():
    """Handle scraping request for one or more zip codes."""
    zip_codes_input = request.form.get('zip_codes', '').strip()
    
    if not zip_codes_input:
        flash('Please enter at least one zip code', 'error')
        return redirect(url_for('index'))
    
    zip_codes = [z.strip() for z in zip_codes_input.replace(',', ' ').split() if z.strip()]
    
    valid_zips = []
    for z in zip_codes:
        if len(z) == 5 and z.isdigit():
            valid_zips.append(z)
        else:
            flash(f'Invalid zip code: {z} (must be 5 digits)', 'warning')
    
    if not valid_zips:
        flash('No valid zip codes provided', 'error')
        return redirect(url_for('index'))
    
    create_sheets = request.form.get('create_sheets') == 'on'
    create_csv = request.form.get('create_csv') == 'on'
    
    results = []
    
    for zip_code in valid_zips:
        try:
            logger.info(f"Starting scrape for zip code: {zip_code}")
            agents = scrape_agents(zip_code)
            
            result = {
                'zip_code': zip_code,
                'agent_count': len(agents),
                'agents': agents,
                'sheet_url': None,
                'csv_path': None,
                'error': None
            }
            
            if agents:
                if create_sheets:
                    try:
                        sheet_url = create_sheet_for_zip(zip_code, agents)
                        result['sheet_url'] = sheet_url
                    except Exception as e:
                        logger.error(f"Google Sheets error for {zip_code}: {e}")
                        result['error'] = f"Sheets error: {str(e)}"
                
                if create_csv:
                    try:
                        csv_path = export_agents_to_ghl_csv(zip_code, agents)
                        result['csv_path'] = csv_path
                        result['csv_filename'] = os.path.basename(csv_path)
                    except Exception as e:
                        logger.error(f"CSV export error for {zip_code}: {e}")
                        result['error'] = f"CSV error: {str(e)}"
            
            results.append(result)
            scrape_results[zip_code] = result
            
        except Exception as e:
            logger.error(f"Scraping error for zip {zip_code}: {e}")
            results.append({
                'zip_code': zip_code,
                'agent_count': 0,
                'agents': [],
                'sheet_url': None,
                'csv_path': None,
                'error': str(e)
            })
    
    return render_template('results.html', results=results)


@app.route('/api/scrape', methods=['POST'])
def api_scrape():
    """API endpoint for scraping (returns JSON)."""
    data = request.get_json() or {}
    zip_codes = data.get('zip_codes', [])
    
    if isinstance(zip_codes, str):
        zip_codes = [z.strip() for z in zip_codes.replace(',', ' ').split() if z.strip()]
    
    if not zip_codes:
        return jsonify({'error': 'No zip codes provided'}), 400
    
    create_sheets = data.get('create_sheets', False)
    create_csv = data.get('create_csv', True)
    
    results = []
    
    for zip_code in zip_codes:
        if not (len(zip_code) == 5 and zip_code.isdigit()):
            results.append({
                'zip_code': zip_code,
                'error': 'Invalid zip code format'
            })
            continue
        
        try:
            agents = scrape_agents(zip_code)
            
            result = {
                'zip_code': zip_code,
                'agent_count': len(agents),
                'agents': agents
            }
            
            if agents:
                if create_sheets:
                    sheet_url = create_sheet_for_zip(zip_code, agents)
                    result['sheet_url'] = sheet_url
                
                if create_csv:
                    csv_path = export_agents_to_ghl_csv(zip_code, agents)
                    result['csv_filename'] = os.path.basename(csv_path)
            
            results.append(result)
            
        except Exception as e:
            results.append({
                'zip_code': zip_code,
                'error': str(e)
            })
    
    return jsonify({'results': results})


@app.route('/download/<filename>')
def download_csv(filename):
    """Download a generated CSV file."""
    if '..' in filename or '/' in filename or '\\' in filename:
        return jsonify({'error': 'Invalid filename'}), 400
    
    filepath = os.path.join(config.OUTPUT_DIR, filename)
    
    if not os.path.exists(filepath):
        return jsonify({'error': 'File not found'}), 404
    
    return send_file(
        filepath,
        mimetype='text/csv',
        as_attachment=True,
        download_name=filename
    )


@app.route('/preview/<zip_code>')
def preview_agents(zip_code):
    """Preview scraped agents for a zip code."""
    if zip_code in scrape_results:
        return render_template(
            'preview.html',
            zip_code=zip_code,
            agents=scrape_results[zip_code].get('agents', [])
        )
    return redirect(url_for('index'))


@app.route('/health')
def health():
    """Health check endpoint."""
    sheets_manager = GoogleSheetsManager()
    return jsonify({
        'status': 'healthy',
        'google_sheets_available': sheets_manager.is_available()
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

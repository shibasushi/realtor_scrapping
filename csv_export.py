import csv
import os
import logging
from datetime import datetime
from typing import Optional

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GHLCSVExporter:
    """Export agent data to GoHighLevel-compatible CSV format with auto-tagging."""
    
    GHL_HEADERS = [
        'firstName',
        'lastName',
        'email',
        'phone',
        'companyName',
        'tags',
        'customField.years_experience',
        'customField.recent_sales',
        'customField.active_listings',
        'customField.rating',
        'customField.specialties',
        'customField.profile_url',
        'customField.source'
    ]
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir or config.OUTPUT_DIR
        os.makedirs(self.output_dir, exist_ok=True)
    
    def export_to_csv(self, zip_code: str, agents: list[dict]) -> str:
        """
        Export agents to a GHL-ready CSV file.
        
        Returns the path to the created CSV file.
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"GHL_Realtor_{zip_code}_{timestamp}.csv"
        filepath = os.path.join(self.output_dir, filename)
        
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.GHL_HEADERS)
            writer.writeheader()
            
            for agent in agents:
                row = self._convert_agent_to_ghl_row(agent, zip_code)
                writer.writerow(row)
        
        logger.info(f"Exported {len(agents)} agents to {filepath}")
        return filepath
    
    def _convert_agent_to_ghl_row(self, agent: dict, zip_code: str) -> dict:
        """Convert an agent dict to a GHL CSV row."""
        first_name, last_name = self._split_name(agent.get('name', ''))
        
        tags = self._generate_tags(agent, zip_code)
        
        return {
            'firstName': first_name,
            'lastName': last_name,
            'email': agent.get('email') or '',
            'phone': self._format_phone(agent.get('phone')),
            'companyName': agent.get('brokerage') or '',
            'tags': tags,
            'customField.years_experience': str(agent.get('years_experience', '')) if agent.get('years_experience') else '',
            'customField.recent_sales': str(agent.get('recent_sales_count', 0)),
            'customField.active_listings': str(agent.get('active_listings', 0)),
            'customField.rating': str(agent.get('rating', '')) if agent.get('rating') else '',
            'customField.specialties': agent.get('specialties') or '',
            'customField.profile_url': agent.get('profile_url') or '',
            'customField.source': 'Realtor.com'
        }
    
    def _split_name(self, full_name: str) -> tuple[str, str]:
        """Split a full name into first and last name."""
        if not full_name:
            return '', ''
        
        parts = full_name.strip().split()
        
        if len(parts) == 1:
            return parts[0], ''
        elif len(parts) == 2:
            return parts[0], parts[1]
        else:
            return parts[0], ' '.join(parts[1:])
    
    def _format_phone(self, phone: Optional[str]) -> str:
        """Format phone number for GHL import."""
        if not phone:
            return ''
        
        digits = ''.join(c for c in phone if c.isdigit())
        
        if len(digits) == 10:
            return f"+1{digits}"
        elif len(digits) == 11 and digits.startswith('1'):
            return f"+{digits}"
        elif len(digits) > 0:
            return phone
        
        return ''
    
    def _generate_tags(self, agent: dict, zip_code: str) -> str:
        """Generate auto-applied tags based on agent data."""
        tags = []
        
        tags.append(f"Zip: {zip_code}")
        
        recent_sales = agent.get('recent_sales_count', 0) or 0
        deal_tag = self._get_deal_volume_tag(recent_sales)
        if deal_tag:
            tags.append(deal_tag)
        
        if agent.get('phone'):
            tags.append('Has Phone')
        else:
            tags.append('No Phone')
        
        if agent.get('email'):
            tags.append('Has Email')
        else:
            tags.append('No Email')
        
        if agent.get('years_experience'):
            years = agent['years_experience']
            if years >= 10:
                tags.append('Exp: 10+ Years')
            elif years >= 5:
                tags.append('Exp: 5-9 Years')
            elif years >= 1:
                tags.append('Exp: 1-4 Years')
            else:
                tags.append('Exp: New Agent')
        
        if agent.get('rating'):
            rating = agent['rating']
            if rating >= 4.5:
                tags.append('Rating: Top Rated')
            elif rating >= 4.0:
                tags.append('Rating: 4+ Stars')
        
        tags.append('Source: Realtor.com')
        
        return ','.join(tags)
    
    def _get_deal_volume_tag(self, sales_count: int) -> str:
        """Get the deal volume tag based on recent sales count."""
        for (min_val, max_val), tag in config.DEAL_TAGS.items():
            if min_val <= sales_count <= max_val:
                return tag
        return 'Deals: 0'


def export_agents_to_ghl_csv(zip_code: str, agents: list[dict]) -> str:
    """Main entry point for exporting agents to GHL CSV."""
    exporter = GHLCSVExporter()
    return exporter.export_to_csv(zip_code, agents)


def export_multiple_zips_to_csv(zip_agents: dict[str, list[dict]]) -> list[str]:
    """Export agents from multiple zip codes to separate CSV files."""
    exporter = GHLCSVExporter()
    files = []
    
    for zip_code, agents in zip_agents.items():
        filepath = exporter.export_to_csv(zip_code, agents)
        files.append(filepath)
    
    return files


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
            'specialties': 'Luxury Homes',
            'profile_url': 'https://example.com/agent/john'
        },
        {
            'name': 'Jane Doe',
            'phone': None,
            'email': 'jane@example.com',
            'brokerage': 'XYZ Properties',
            'years_experience': 3,
            'recent_sales_count': 8,
            'active_listings': 2,
            'rating': 4.2,
            'specialties': 'First-Time Buyers',
            'profile_url': 'https://example.com/agent/jane'
        },
        {
            'name': 'Bob Wilson',
            'phone': '555-987-6543',
            'email': None,
            'brokerage': 'Premier Realty',
            'years_experience': 15,
            'recent_sales_count': 45,
            'active_listings': 12,
            'rating': 4.9,
            'specialties': 'Commercial, Investment',
            'profile_url': 'https://example.com/agent/bob'
        }
    ]
    
    filepath = export_agents_to_ghl_csv('90210', test_agents)
    print(f"Created test CSV: {filepath}")
    
    print("\nCSV Contents:")
    with open(filepath, 'r') as f:
        print(f.read())

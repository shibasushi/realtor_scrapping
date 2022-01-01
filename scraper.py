import json
import re
import time
import logging
from typing import Optional
from dataclasses import dataclass, asdict
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class AgentData:
    name: str
    phone: Optional[str]
    email: Optional[str]
    brokerage: Optional[str]
    years_experience: Optional[int]
    recent_sales_count: int
    active_listings: int
    rating: Optional[float]
    specialties: str
    profile_url: str
    photo_url: Optional[str]
    
    def to_dict(self) -> dict:
        return asdict(self)


class RealtorScraper:
    BASE_URL = 'https://www.realtor.com'
    AGENT_SEARCH_URL = 'https://www.realtor.com/realestateagents/{zip_code}'
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.USER_AGENT,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_zip_code(self, zip_code: str) -> list[AgentData]:
        """Scrape all agents for a given zip code."""
        all_agents = []
        page = 1
        
        while True:
            logger.info(f"Scraping zip {zip_code}, page {page}")
            agents, has_more = self._scrape_page(zip_code, page)
            all_agents.extend(agents)
            
            if not has_more or not agents:
                break
            
            page += 1
            time.sleep(config.REQUEST_DELAY)
        
        all_agents.sort(key=lambda x: x.recent_sales_count, reverse=True)
        logger.info(f"Found {len(all_agents)} agents for zip {zip_code}")
        return all_agents
    
    def _scrape_page(self, zip_code: str, page: int = 1) -> tuple[list[AgentData], bool]:
        """Scrape a single page of agent results."""
        url = self.AGENT_SEARCH_URL.format(zip_code=zip_code)
        if page > 1:
            url = f"{url}/pg-{page}"
        
        for attempt in range(config.MAX_RETRIES):
            try:
                response = self.session.get(url, timeout=config.REQUEST_TIMEOUT)
                response.raise_for_status()
                break
            except requests.RequestException as e:
                logger.warning(f"Request failed (attempt {attempt + 1}): {e}")
                if attempt == config.MAX_RETRIES - 1:
                    raise
                time.sleep(config.REQUEST_DELAY * (attempt + 1))
        
        return self._parse_response(response.text, zip_code)
    
    def _parse_response(self, html: str, zip_code: str) -> tuple[list[AgentData], bool]:
        """Parse the HTML response and extract agent data from NEXT_DATA."""
        soup = BeautifulSoup(html, 'lxml')
        
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if not next_data_script:
            logger.warning("No __NEXT_DATA__ script found, trying fallback parsing")
            return self._fallback_parse(soup), False
        
        try:
            data = json.loads(next_data_script.string)
            return self._extract_agents_from_next_data(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse NEXT_DATA JSON: {e}")
            return self._fallback_parse(soup), False
    
    def _extract_agents_from_next_data(self, data: dict) -> tuple[list[AgentData], bool]:
        """Extract agent information from the NEXT_DATA JSON structure."""
        agents = []
        has_more = False
        
        try:
            props = data.get('props', {})
            page_props = props.get('pageProps', {})
            
            agents_data = None
            pagination = None
            
            if 'agents' in page_props:
                agents_data = page_props['agents']
                pagination = page_props.get('pagination', {})
            elif 'searchResults' in page_props:
                search_results = page_props['searchResults']
                agents_data = search_results.get('agents', [])
                pagination = search_results.get('pagination', {})
            elif 'agentList' in page_props:
                agents_data = page_props['agentList']
                pagination = page_props.get('pagination', {})
            
            if not agents_data:
                for key, value in page_props.items():
                    if isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], dict) and any(
                            k in value[0] for k in ['full_name', 'name', 'agent_name', 'display_name']
                        ):
                            agents_data = value
                            break
                    elif isinstance(value, dict):
                        if 'agents' in value:
                            agents_data = value['agents']
                            pagination = value.get('pagination', {})
                            break
                        elif 'results' in value:
                            agents_data = value['results']
                            pagination = value.get('pagination', {})
                            break
            
            if agents_data:
                for agent_raw in agents_data:
                    agent = self._parse_agent_data(agent_raw)
                    if agent:
                        agents.append(agent)
            
            if pagination:
                current = pagination.get('current_page', pagination.get('page', 1))
                total = pagination.get('total_pages', pagination.get('pages', 1))
                has_more = current < total
            
        except Exception as e:
            logger.error(f"Error extracting agents from NEXT_DATA: {e}")
        
        return agents, has_more
    
    def _parse_agent_data(self, raw: dict) -> Optional[AgentData]:
        """Parse individual agent data from various possible JSON structures."""
        try:
            name = (
                raw.get('full_name') or 
                raw.get('name') or 
                raw.get('agent_name') or
                raw.get('display_name') or
                f"{raw.get('first_name', '')} {raw.get('last_name', '')}".strip()
            )
            
            if not name:
                return None
            
            phones = raw.get('phones', [])
            phone = None
            if phones:
                if isinstance(phones[0], dict):
                    phone = phones[0].get('number') or phones[0].get('phone')
                elif isinstance(phones[0], str):
                    phone = phones[0]
            if not phone:
                phone = raw.get('phone') or raw.get('office_phone') or raw.get('mobile_phone')
            
            email = raw.get('email') or raw.get('agent_email')
            
            office = raw.get('office', {})
            brokerage = (
                raw.get('brokerage') or 
                raw.get('broker', {}).get('name') or
                office.get('name') or
                raw.get('office_name')
            )
            
            years_exp = raw.get('years_of_experience') or raw.get('experience_years')
            if years_exp is not None:
                try:
                    years_exp = int(years_exp)
                except (ValueError, TypeError):
                    years_exp = None
            
            sales_data = raw.get('recently_sold', {})
            if isinstance(sales_data, dict):
                recent_sales = sales_data.get('count', 0)
            else:
                recent_sales = raw.get('recent_sales_count', 0) or raw.get('sold_count', 0)
            
            try:
                recent_sales = int(recent_sales) if recent_sales else 0
            except (ValueError, TypeError):
                recent_sales = 0
            
            listings_data = raw.get('for_sale', {})
            if isinstance(listings_data, dict):
                active_listings = listings_data.get('count', 0)
            else:
                active_listings = raw.get('active_listings', 0) or raw.get('listing_count', 0)
            
            try:
                active_listings = int(active_listings) if active_listings else 0
            except (ValueError, TypeError):
                active_listings = 0
            
            rating = raw.get('rating') or raw.get('review_score') or raw.get('average_rating')
            if rating is not None:
                try:
                    rating = float(rating)
                except (ValueError, TypeError):
                    rating = None
            
            specialties_list = raw.get('specializations', []) or raw.get('specialties', [])
            if isinstance(specialties_list, list):
                if specialties_list and isinstance(specialties_list[0], dict):
                    specialties = ', '.join(s.get('name', '') for s in specialties_list if s.get('name'))
                else:
                    specialties = ', '.join(str(s) for s in specialties_list)
            else:
                specialties = str(specialties_list) if specialties_list else ''
            
            profile_url = raw.get('href') or raw.get('profile_url') or raw.get('web_url') or ''
            if profile_url and not profile_url.startswith('http'):
                profile_url = urljoin(self.BASE_URL, profile_url)
            
            photo_url = raw.get('photo', {}).get('href') if isinstance(raw.get('photo'), dict) else raw.get('photo')
            if not photo_url:
                photo_url = raw.get('image_url') or raw.get('avatar')
            
            return AgentData(
                name=name,
                phone=phone,
                email=email,
                brokerage=brokerage,
                years_experience=years_exp,
                recent_sales_count=recent_sales,
                active_listings=active_listings,
                rating=rating,
                specialties=specialties,
                profile_url=profile_url,
                photo_url=photo_url
            )
            
        except Exception as e:
            logger.error(f"Error parsing agent data: {e}")
            return None
    
    def _fallback_parse(self, soup: BeautifulSoup) -> list[AgentData]:
        """Fallback HTML parsing if NEXT_DATA is not available."""
        agents = []
        
        agent_cards = soup.select('[data-testid="agent-card"], .agent-card, .agent-list-card')
        
        for card in agent_cards:
            try:
                name_elem = card.select_one('[data-testid="agent-name"], .agent-name, h2, h3')
                name = name_elem.get_text(strip=True) if name_elem else None
                
                if not name:
                    continue
                
                phone_elem = card.select_one('[data-testid="agent-phone"], .agent-phone, a[href^="tel:"]')
                phone = None
                if phone_elem:
                    if phone_elem.get('href', '').startswith('tel:'):
                        phone = phone_elem['href'].replace('tel:', '')
                    else:
                        phone = phone_elem.get_text(strip=True)
                
                brokerage_elem = card.select_one('[data-testid="agent-brokerage"], .agent-brokerage, .office-name')
                brokerage = brokerage_elem.get_text(strip=True) if brokerage_elem else None
                
                link_elem = card.select_one('a[href*="/realestateagents/"]')
                profile_url = ''
                if link_elem and link_elem.get('href'):
                    profile_url = urljoin(self.BASE_URL, link_elem['href'])
                
                agents.append(AgentData(
                    name=name,
                    phone=phone,
                    email=None,
                    brokerage=brokerage,
                    years_experience=None,
                    recent_sales_count=0,
                    active_listings=0,
                    rating=None,
                    specialties='',
                    profile_url=profile_url,
                    photo_url=None
                ))
                
            except Exception as e:
                logger.error(f"Error in fallback parsing: {e}")
                continue
        
        return agents


def scrape_agents(zip_code: str) -> list[dict]:
    """Main entry point for scraping agents by zip code."""
    scraper = RealtorScraper()
    agents = scraper.scrape_zip_code(zip_code)
    return [agent.to_dict() for agent in agents]


if __name__ == '__main__':
    import sys
    
    zip_code = sys.argv[1] if len(sys.argv) > 1 else '90210'
    agents = scrape_agents(zip_code)
    print(f"\nFound {len(agents)} agents for zip code {zip_code}")
    for agent in agents[:5]:
        print(f"\n{agent['name']}")
        print(f"  Phone: {agent['phone']}")
        print(f"  Email: {agent['email']}")
        print(f"  Recent Sales: {agent['recent_sales_count']}")

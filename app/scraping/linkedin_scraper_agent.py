import time
import random
import logging
from typing import Dict
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

class LinkedInScraperAgent:
    """
    Scrapes public LinkedIn profile data: bio, experience, recent posts.
    Uses random delays, user-agent spoofing, waits, and error handling for production robustness.
    """
    def __init__(self, headless: bool = True, min_delay: int = 15, max_delay: int = 30):
        chrome_options = Options()
        if headless:
            chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
        self.driver = webdriver.Chrome(options=chrome_options)
        self.min_delay = min_delay
        self.max_delay = max_delay
        logging.basicConfig(level=logging.INFO)

    def scrape_profile(self, url: str) -> Dict[str, str]:
        try:
            self.driver.get(url)
            # Wait for the main content to load (up to 15s)
            try:
                WebDriverWait(self.driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'main'))
                )
            except Exception as e:
                logging.warning(f"Timeout waiting for LinkedIn main content: {e}")
                return {'bio': '', 'experience': '', 'recent_posts': '', 'error': 'Timeout or blocked'}
            soup = BeautifulSoup(self.driver.page_source, 'html.parser')
            # Bio
            bio = soup.find('div', {'class': 'text-body-medium'})
            bio_text = bio.get_text(strip=True) if bio else ''
            # Experience (try several selectors for robustness)
            exp_blocks = soup.find_all('span', {'class': 'mr1'})
            experience = '\n'.join([li.get_text(strip=True) for li in exp_blocks])
            # Recent posts (up to 3)
            posts = '\n'.join([p.get_text(strip=True) for p in soup.find_all('span', {'dir': 'ltr'})][:3])
            # Random delay to avoid rate limiting
            delay = random.randint(self.min_delay, self.max_delay)
            logging.info(f"Sleeping {delay}s to respect LinkedIn rate limits...")
            time.sleep(delay)
            return {
                'bio': bio_text,
                'experience': experience,
                'recent_posts': posts,
                'error': ''
            }
        except Exception as e:
            logging.error(f"Failed to scrape {url}: {e}")
            return {'bio': '', 'experience': '', 'recent_posts': '', 'error': str(e)}

    def close(self):
        self.driver.quit()

import time
import re
import os
import shutil
from pathlib import Path
from typing import Dict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import logging

class LinkedInProfileTextScraperAgent:
    """
    Scrapes LinkedIn profiles and extracts all visible profile text using Selenium.
    Uses a persistent Chrome profile for login.
    """
    def __init__(self, chrome_profile_dir="chrome_profile", download_dir="linkedin_scrapes", headless=False):
        self.chrome_profile_dir = str(Path(chrome_profile_dir).absolute())
        self.download_dir = str(Path(download_dir).absolute())
        Path(self.download_dir).mkdir(exist_ok=True)
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument(f'--user-data-dir={self.chrome_profile_dir}')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        prefs = {"download.default_directory": self.download_dir,
                 "download.prompt_for_download": False,
                 "download.directory_upgrade": True,
                 "plugins.always_open_pdf_externally": True}
        chrome_options.add_experimental_option("prefs", prefs)
        if headless:
            chrome_options.add_argument('--headless=new')
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        logging.basicConfig(level=logging.INFO)

    def login_if_needed(self, email, password):
        self.driver.get("https://www.linkedin.com/feed/")
        time.sleep(3)
        if "login" in self.driver.current_url:
            self.driver.get("https://www.linkedin.com/login")
            time.sleep(2)
            email_input = self.driver.find_element(By.ID, "username")
            pw_input = self.driver.find_element(By.ID, "password")
            email_input.send_keys(email)
            pw_input.send_keys(password)
            pw_input.send_keys(Keys.RETURN)
            time.sleep(4)

    def scrape_profile_text(self, profile_url: str, user_name_hint: str = "") -> Dict[str, str]:
        logging.info(f"[LinkedIn] Navigating to profile URL: {profile_url}")
        self.driver.get(profile_url)
        time.sleep(3)
        try:
            logging.info("[LinkedIn] Starting to scroll the page to load dynamic content...")
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            while True:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                logging.info(f"[LinkedIn] Scrolled to bottom, waiting for content... (attempt {scroll_attempts+1})")
                time.sleep(1.5)  # Wait for new content to load
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts > 2:
                        logging.info("[LinkedIn] No more content loaded after scrolling. Done.")
                        break
                else:
                    last_height = new_height
                    scroll_attempts = 0
            time.sleep(1)
            logging.info("[LinkedIn] Extracting all visible text from profile page...")
            body = self.driver.find_element(By.TAG_NAME, 'body')
            profile_text = body.text
            logging.info(f"[LinkedIn] Extracted {len(profile_text)} characters of text from profile.")
            return {'profile_text': profile_text, 'error': ''}
        except Exception as e:
            logging.error(f"[LinkedIn] Error scraping profile: {e}")
            return {'profile_text': '', 'error': str(e)}

    def close(self):
        self.driver.quit()

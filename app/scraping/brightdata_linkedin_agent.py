import requests
from typing import List, Dict, Optional
from time import sleep
import streamlit as st

BRIGHTDATA_API_KEY = st.secrets["BRIGHTDATA_API_KEY"]
TRIGGER_URL = "https://api.brightdata.com/datasets/v3/trigger?dataset_id=gd_l1viktl72bvl7bjuj0&include_errors=true"
SNAPSHOT_URL_TEMPLATE = "https://api.brightdata.com/datasets/v3/snapshot/{snapshot_id}?format=json"

class BrightDataLinkedInAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or BRIGHTDATA_API_KEY
        if not self.api_key:
            raise ValueError("Bright Data API key not found. Set BRIGHTDATA_API_KEY in your Streamlit secrets.")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def trigger_profiles(self, linkedin_urls: List[str]) -> str:
        if len(linkedin_urls) > 10:
            raise ValueError("You can only send up to 10 LinkedIn URLs at once.")
        data = [{"url": url} for url in linkedin_urls]
        resp = requests.post(TRIGGER_URL, headers=self.headers, json=data)
        resp.raise_for_status()
        result = resp.json()
        # Expecting snapshot_id in response
        snapshot_id = result.get("snapshot_id")
        if not snapshot_id:
            # Try to get from first item in 'snapshots' if present
            snapshots = result.get("snapshots")
            if snapshots and isinstance(snapshots, list) and len(snapshots) > 0:
                snapshot_id = snapshots[0].get("id")
        if not snapshot_id:
            raise RuntimeError(f"Could not retrieve snapshot_id from Bright Data response: {result}")
        return snapshot_id

    def fetch_snapshot(self, snapshot_id: str, max_wait_sec: int = 300, wait_sec: int = 5) -> List[Dict]:
        import logging
        import time
        url = SNAPSHOT_URL_TEMPLATE.format(snapshot_id=snapshot_id)
        start_time = time.time()
        attempt = 0
        while True:
            attempt += 1
            resp = requests.get(url, headers=self.headers)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, list) and data:
                        logging.info(f"[BrightDataLinkedInAgent] Snapshot {snapshot_id} ready after {attempt} attempts.")
                        return data
                except Exception as e:
                    logging.error(f"[BrightDataLinkedInAgent] Error parsing snapshot JSON: {e}")
            elapsed = time.time() - start_time
            if elapsed > max_wait_sec:
                logging.error(f"[BrightDataLinkedInAgent] Timeout: Snapshot {snapshot_id} not ready after {elapsed:.1f} seconds.")
                break
            logging.info(f"[BrightDataLinkedInAgent] Waiting for snapshot {snapshot_id}, attempt {attempt}, elapsed {elapsed:.1f}s...")
            time.sleep(wait_sec)
        raise RuntimeError(f"Snapshot {snapshot_id} not ready after {max_wait_sec} seconds.")

    def scrape_linkedin_profiles(self, linkedin_urls: List[str]) -> List[Dict]:
        snapshot_id = self.trigger_profiles(linkedin_urls)
        return self.fetch_snapshot(snapshot_id)

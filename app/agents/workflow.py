from app.agents.course_persona_agent import CoursePersonaAgent
from app.scraping.brightdata_linkedin_agent import BrightDataLinkedInAgent
from app.email_gen.email_generation_agent import EmailGenerationAgent
from app.db.db_connector import SupabaseConnector, MongoDBConnector
from app.utils.pdf_utils import extract_pdf_text
import pandas as pd

class OutreachWorkflow:
    def __init__(self, db_type='supabase', linkedin_email=None, linkedin_password=None):
        self.course_persona_agent = CoursePersonaAgent()
        self.linkedin_scraper = BrightDataLinkedInAgent()
        self.email_agent = EmailGenerationAgent()
        self.db = SupabaseConnector() if db_type == 'supabase' else MongoDBConnector()
        self.linkedin_email = linkedin_email
        self.linkedin_password = linkedin_password

    def run(self, course_details: str, persona: str, user_df: pd.DataFrame):
        import logging
        logging.info("[Workflow] Loading course details and persona...")
        self.course_persona_agent.load(course_details, persona)
        context = self.course_persona_agent.get_context()
        results = []
        # Robust LinkedIn column detection (case-insensitive)
        linkedin_col = None
        for col in user_df.columns:
            if col.strip().lower() in ['linkedin', 'linkedin_url', 'linkedin profile', 'profile_link', 'linkedinprofile']:
                linkedin_col = col
                break
        if not linkedin_col:
            print(f"No LinkedIn column found. Columns detected: {list(user_df.columns)}")
            return []
        # No login needed with Bright Data API
        import random
        # Batch LinkedIn URLs in groups of up to 10 for Bright Data API
        linkedin_urls = [row.get(linkedin_col) for _, row in user_df.iterrows() if row.get(linkedin_col) and isinstance(row.get(linkedin_col), str) and row.get(linkedin_col).strip()]
        profile_results = []
        for i in range(0, len(linkedin_urls), 10):
            batch = linkedin_urls[i:i+10]
            try:
                batch_results = self.linkedin_scraper.scrape_linkedin_profiles(batch)
                profile_results.extend(batch_results)
            except Exception as e:
                logging.error(f"[Workflow] Error scraping batch {i//10+1}: {e}")
        # Map results by URL for lookup
        url_to_profile = {item.get('url') or item.get('input', {}).get('url'): item for item in profile_results}
        for idx, row in user_df.iterrows():
            linkedin_url = row.get(linkedin_col)
            if not linkedin_url or not isinstance(linkedin_url, str) or not linkedin_url.strip():
                logging.warning(f"[Workflow] Skipping row {idx+1}: No valid LinkedIn URL found.")
                continue
            logging.info(f"[Workflow] Processing row {idx+1} of {len(user_df)}.")
            profile_data = url_to_profile.get(linkedin_url.strip(), {})
            # Use the entire Bright Data JSON profile for Claude
            profile_json = profile_data if profile_data else {}
            profile_error = '' if profile_data else 'No profile data returned'
            logging.info(f"[Workflow] Scraped profile for row {idx+1}: {profile_json}")
            if profile_error:
                logging.error(f"[Workflow] Error scraping profile for row {idx+1}: {profile_error}")
            # Get the email address for this user from the uploaded file
            email_value = None
            for possible_email_col in ['email', 'Email', 'EMAIL']:
                if possible_email_col in row and pd.notnull(row[possible_email_col]):
                    email_value = row[possible_email_col]
                    break
            # Save user data for database insertion
            name_value = row.get('First Name') or row.get('Name') or row.get('name')
            db_record = {
                'name': name_value,
                'email': email_value,
                'linkedin_url': linkedin_url,
                'email_draft': '',
                'profile_json': profile_json,
                'profile_error': profile_error,
                'email_error': ''
            }
            try:
                logging.info(f"[Workflow] Inserting scraped data for row {idx+1} into database...")
                self.db.insert('outreach_results', db_record)
                logging.info(f"[Workflow] Successfully inserted row {idx+1} into database.")
            except Exception as e:
                logging.error(f"[Workflow] Database insert failed for row {idx+1}: {e}")
            # Prepare user profile data for email generation
            profile = {
                'profile_json': profile_json
            }
            email = ''
            email_error = ''
            if profile_json and not profile_error:
                try:
                    logging.info(f"[Workflow] Sending profile, course details, and persona to Claude for row {idx+1}...")
                    # Generate an email draft based on the user's profile and course context
                    email = self.email_agent.generate_email(context, profile)
                    logging.info(f"[Workflow] Email draft generated for row {idx+1}.")
                except Exception as e:
                    email_error = f"Email generation error: {e}"
                    logging.error(f"[Workflow] Email generation failed for row {idx+1}: {e}")
            # Add the email draft to the results list and insert into the drafted emails table
            result = {
                'name': db_record['name'],
                'email': db_record['email'],
                'linkedin_url': linkedin_url,
                'email_draft': email,
                'profile_error': profile_error,
                'email_error': email_error
            }
            results.append(result)
            try:
                self.db.insert('drafted_emails', {
                    'name': name_value,
                    'email': email_value,
                    'email_draft': email
                })
            except Exception as e:
                logging.error(f"[Workflow] Failed to insert drafted email for row {idx+1}: {e}")
            # Wait 1-2 seconds between requests to avoid rate-limiting
            import time
            import random
            delay = random.uniform(1, 2)
            logging.info(f"[Workflow] Waiting {delay:.2f} seconds before next profile...")
            time.sleep(delay)
        # No close needed for Bright Data agent
        if not results:
            print(f"No valid LinkedIn URLs found in column '{linkedin_col}'.")
        return results

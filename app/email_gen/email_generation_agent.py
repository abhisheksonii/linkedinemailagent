import os
import requests
from typing import Dict

class EmailGenerationAgent:
    """
    Generates personalized emails using the Claude API, based on the provided context and profile data.
    """
    def __init__(self):
        import streamlit as st
        self.api_key = st.secrets.get('CLAUDE_API_KEY') or st.secrets.get('ANTHROPIC_API_KEY')
        self.api_url = 'https://api.anthropic.com/v1/messages'
        self.model = 'claude-3-5-haiku-20241022'  # Or another Claude model

    def _clean_and_summarize_profile_text(self, profile_text: str) -> str:
        """
        Basic cleaning and summarization of the LinkedIn profile text.
        Removes redundant whitespace, collapses repeated lines, and truncates if too long.
        """
        import re
        lines = [line.strip() for line in profile_text.splitlines() if line.strip()]
        # Remove duplicate lines while preserving order
        seen = set()
        unique_lines = []
        for line in lines:
            if line not in seen:
                unique_lines.append(line)
                seen.add(line)
        cleaned = '\n'.join(unique_lines)
        # Truncate to the first 1200 words for prompt brevity
        words = cleaned.split()
        if len(words) > 1200:
            cleaned = ' '.join(words[:1200]) + '\n...[truncated]'
        return cleaned

    def generate_email(self, context: Dict[str, str], profile: Dict[str, str]) -> str:
        import logging
        import json
        # Use the full LinkedIn JSON profile
        profile_json = profile.get('profile_json', {})
        profile_json_str = json.dumps(profile_json, indent=2, ensure_ascii=False)
        prompt = self._build_prompt(context, profile_json_str)
        logging.info(f"[EmailGenerationAgent] Sending prompt to Claude: {prompt}")
        headers = {
            'x-api-key': self.api_key,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json'
        }
        data = {
            "model": self.model,
            "max_tokens": 512,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        resp = requests.post(self.api_url, headers=headers, json=data)
        logging.info(f"[EmailGenerationAgent] Claude API response: {resp.status_code} {resp.text}")
        if resp.status_code == 200:
            return resp.json().get('content', [{}])[0].get('text', '').strip()
        else:
            return f"[Error from Claude API: {resp.status_code}] {resp.text}"

    def _build_prompt(self, context: Dict[str, str], profile_json_str: str) -> str:
        # Prompt tells Claude to return only the outreach email draft, without extra comments
        return f"""
You are an expert outreach copywriter. Write a hyper-personalized cold outreach email draft for a prospective learner using:
- The course or offering details
- The target persona
- The full LinkedIn profile JSON below

Return ONLY the outreach email draft. Do NOT include any comments, explanations, or extra text.

Course Details:
{context['course_details']}

Persona:
{context['persona']}

LinkedIn Profile JSON:
{profile_json_str}
"""

"""
AI Parser Module
Uses improved regex patterns first, then falls back to Claude Sonnet 4
via OpenRouter for extraction when regex fails. Supports vision API for image-based resumes.
"""

import re
import os
import json
import base64
import requests
from typing import Optional, Dict, Any, Tuple, List
from PIL import Image
import io


OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "anthropic/claude-sonnet-4"


EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

PHONE_PATTERNS = [
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(\+61\s?[2-9](?:[\s.-]?\d){8})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(\+61\s?4\d{2}(?:[\s.-]?\d){6})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(04\d{2}[\s.-]?\d{3}[\s.-]?\d{3})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(04\d{8})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(0[2-9]\d{2}[\s.-]?\d{3}[\s.-]?\d{3})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(0[2-9]\s?\d{4}\s?\d{4})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(\(\+?61\)\s?[2-9](?:[\s.-]?\d){8})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(\+61\s?[2-9]\d{8})', re.IGNORECASE),
    re.compile(r'(?:Phone:?\s*|Mobile:?\s*|Tel:?\s*|Ph:?\s*)?(0[2-9]\d{8})', re.IGNORECASE),
]

SKIP_WORDS = {
    'resume', 'cv', 'curriculum', 'vitae', 'profile', 'summary',
    'objective', 'experience', 'education', 'skills', 'contact',
    'phone', 'email', 'address', 'mobile', 'tel', 'linkedin',
    'github', 'portfolio', 'website', 'references', 'personal',
    'professional', 'career', 'work', 'employment', 'history',
    'background', 'overview', 'introduction', 'about', 'me',
    'certifications', 'certificates', 'training', 'qualifications'
}

NAME_PREFIXES = {'mr', 'mrs', 'ms', 'miss', 'dr', 'prof', 'sir', 'madam'}


def extract_email(text: str) -> Optional[str]:
    """Extract first email address from text."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract first phone number from text using multiple patterns."""
    for pattern in PHONE_PATTERNS:
        match = pattern.search(text)
        if match:
            phone = match.group(1) if match.lastindex else match.group(0)
            phone = re.sub(r'[\s.-]+', ' ', phone).strip()
            digits_only = re.sub(r'\D', '', phone)
            if 9 <= len(digits_only) <= 12:
                return phone
    return None


def extract_name(text: str) -> Optional[str]:
    """
    Extract candidate name using improved heuristics.
    Name is usually the first prominent text in a resume.
    """
    lines = text.split('\n')
    
    for line in lines[:15]:
        line = line.strip()
        
        if not line or len(line) < 3:
            continue
        
        lower_line = line.lower()
        
        skip = False
        for skip_word in SKIP_WORDS:
            if lower_line == skip_word or lower_line.startswith(skip_word + ':') or lower_line.startswith(skip_word + ' '):
                if not any(c.isupper() for c in line[len(skip_word):].strip()[:1]):
                    skip = True
                    break
        if skip:
            continue
        
        if '@' in line:
            continue
        
        digit_count = sum(c.isdigit() for c in line)
        if digit_count > 3:
            continue
        
        if len(line) > 60:
            continue
        
        cleaned_line = line
        for prefix in NAME_PREFIXES:
            if lower_line.startswith(prefix + ' ') or lower_line.startswith(prefix + '.'):
                cleaned_line = line[len(prefix):].strip()
                if cleaned_line.startswith('.'):
                    cleaned_line = cleaned_line[1:].strip()
                break
        
        words = cleaned_line.split()
        if 1 <= len(words) <= 5:
            valid_words = []
            for word in words:
                clean_word = word.replace('-', '').replace("'", '').replace('.', '')
                if clean_word and clean_word[0].isupper() and clean_word.isalpha():
                    valid_words.append(word)
                elif clean_word.isupper() and len(clean_word) > 1:
                    valid_words.append(word)
            
            if len(valid_words) >= 1 and len(valid_words) == len(words):
                return cleaned_line
    
    return None


def extract_name_from_email(email: str) -> Optional[str]:
    """
    Try to extract a name from an email address.
    e.g., john.doe@email.com -> John Doe
    """
    if not email:
        return None
    
    local_part = email.split('@')[0]
    
    local_part = re.sub(r'\d+', '', local_part)
    
    parts = re.split(r'[._-]', local_part)
    
    name_parts = []
    for part in parts:
        if len(part) > 1:
            name_parts.append(part.capitalize())
    
    if len(name_parts) >= 2:
        return ' '.join(name_parts)
    
    return None


def extract_with_regex(text: str) -> Dict[str, Optional[str]]:
    """
    Extract name, email, and phone using regex patterns.
    
    Returns:
        Dictionary with 'name', 'email', 'phone' keys
    """
    email = extract_email(text)
    phone = extract_phone(text)
    name = extract_name(text)
    
    if not name and email:
        name = extract_name_from_email(email)
    
    return {
        'name': name,
        'email': email,
        'phone': phone
    }


def get_api_key() -> Optional[str]:
    """Get OpenRouter API key from environment."""
    return os.environ.get('CLAUDE_SONNET_API_KEY')


def extract_with_ai_text(text: str) -> Tuple[Dict[str, Optional[str]], bool, Optional[str]]:
    """
    Extract information using Claude Sonnet 4 via OpenRouter API for text.
    
    Args:
        text: Resume text to analyze
        
    Returns:
        Tuple of (extracted_data, success, error_message)
    """
    api_key = get_api_key()
    if not api_key:
        return {}, False, "No API key configured"
    
    text_truncated = text[:6000] if len(text) > 6000 else text
    
    prompt = f"""Analyze this resume text and extract the following information.
Return ONLY a JSON object with these exact keys: "name", "email", "phone"
If any field cannot be found, use null for that field.

For the name field:
- Extract the full name of the candidate (first name and last name)
- Remove any prefixes like Mr, Mrs, Ms, Dr
- If the name has "MR JAMES HOMANS" format, extract as "James Homans"

For the phone field:
- Extract the phone number in its original format
- Australian mobile numbers typically start with 04
- Include country code if present

Resume text:
{text_truncated}

Return ONLY the JSON object, no other text."""

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Resume Parser"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0
            },
            timeout=30
        )
        
        if response.status_code == 402:
            return {}, False, "Insufficient AI credits"
        elif response.status_code == 429:
            return {}, False, "AI rate limit exceeded"
        elif response.status_code != 200:
            return {}, False, f"AI API error: {response.status_code}"
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        try:
            if '```' in content:
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            data = json.loads(content.strip())
            return {
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone')
            }, True, None
            
        except json.JSONDecodeError:
            return {}, False, "Failed to parse AI response"
            
    except requests.exceptions.Timeout:
        return {}, False, "AI request timed out"
    except requests.exceptions.RequestException as e:
        return {}, False, f"AI request failed: {str(e)}"


def extract_with_ai_vision(images: List[Image.Image]) -> Tuple[Dict[str, Optional[str]], bool, Optional[str]]:
    """
    Extract information using Claude Sonnet 4 Vision via OpenRouter API for image-based resumes.
    
    Args:
        images: List of PIL Image objects (resume pages)
        
    Returns:
        Tuple of (extracted_data, success, error_message)
    """
    api_key = get_api_key()
    if not api_key:
        return {}, False, "No API key configured"
    
    if not images:
        return {}, False, "No images provided"
    
    try:
        image_contents = []
        for img in images[:1]:
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode('utf-8')
            
            image_contents.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{img_base64}"
                }
            })
        
        image_contents.append({
            "type": "text",
            "text": """Analyze this resume image and extract the following information.
Return ONLY a JSON object with these exact keys: "name", "email", "phone"
If any field cannot be found, use null for that field.

For the name field:
- Extract the full name of the candidate (first name and last name)
- Remove any prefixes like Mr, Mrs, Ms, Dr
- If the name appears as "MR JAMES HOMANS", extract as "James Homans"

For the phone field:
- Extract the phone number in its original format
- Australian mobile numbers typically start with 04
- Include country code if present

Return ONLY the JSON object, no other text."""
        })
        
        response = requests.post(
            OPENROUTER_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Resume Parser"
            },
            json={
                "model": OPENROUTER_MODEL,
                "messages": [
                    {"role": "user", "content": image_contents}
                ],
                "max_tokens": 500,
                "temperature": 0
            },
            timeout=60
        )
        
        if response.status_code == 402:
            return {}, False, "Insufficient AI credits"
        elif response.status_code == 429:
            return {}, False, "AI rate limit exceeded"
        elif response.status_code != 200:
            return {}, False, f"AI API error: {response.status_code}"
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        try:
            if '```' in content:
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
            
            data = json.loads(content.strip())
            return {
                'name': data.get('name'),
                'email': data.get('email'),
                'phone': data.get('phone')
            }, True, None
            
        except json.JSONDecodeError:
            return {}, False, "Failed to parse AI response"
            
    except requests.exceptions.Timeout:
        return {}, False, "AI vision request timed out"
    except requests.exceptions.RequestException as e:
        return {}, False, f"AI vision request failed: {str(e)}"


def check_ai_credits() -> Tuple[bool, Optional[str]]:
    """
    Check if the API key is configured.
    
    Returns:
        Tuple of (has_credits, error_message)
    """
    api_key = get_api_key()
    if not api_key:
        return False, "No API key configured"
    
    return True, None


def process_resume(text: str, is_image_based: bool = False, images: Optional[List[Image.Image]] = None) -> Dict[str, Any]:
    """
    Process resume: try regex first, fallback to AI if needed.
    For image-based PDFs, use vision API directly.
    
    Args:
        text: Resume text
        is_image_based: Whether this is an image-based resume
        images: List of PIL Image objects for vision processing
        
    Returns:
        Dictionary with extraction results and metadata
    """
    result = {
        'name': None,
        'email': None,
        'phone': None,
        'ai_used': False,
        'error': None
    }
    
    if is_image_based and images:
        ai_result, success, error = extract_with_ai_vision(images)
        
        if success:
            result['ai_used'] = True
            result['name'] = ai_result.get('name')
            result['email'] = ai_result.get('email')
            result['phone'] = ai_result.get('phone')
        else:
            result['error'] = error
        
        return result
    
    regex_result = extract_with_regex(text)
    result.update(regex_result)
    
    missing_fields = [k for k in ['name', 'email', 'phone'] if not result[k]]
    
    if missing_fields:
        has_credits, credit_error = check_ai_credits()
        
        if has_credits:
            ai_result, success, error = extract_with_ai_text(text)
            
            if success:
                result['ai_used'] = True
                for field in missing_fields:
                    if ai_result.get(field):
                        result[field] = ai_result[field]
            elif error:
                result['error'] = error
        elif credit_error and not result['name'] and not result['email'] and not result['phone']:
            result['error'] = credit_error
    
    return result

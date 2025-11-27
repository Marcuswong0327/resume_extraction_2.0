"""
AI Parser Module
Uses Claude Sonnet 4 via OpenRouter for name extraction.
Uses regex for email, and regex + AI validation for phone numbers.
Includes confidence scores for all extracted fields.
"""

import re
import os
import json
import requests
from typing import Optional, Dict, Any, Tuple


EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

PHONE_PATTERNS = [
    re.compile(r'\+61\s?4\d{2}[\s-]?\d{3}[\s-]?\d{3}'),
    re.compile(r'04\d{2}[\s-]?\d{3}[\s-]?\d{3}'),
    re.compile(r'04\d{8}'),
    re.compile(r'\+61\s?[2-478][\s-]?\d{4}[\s-]?\d{4}'),
    re.compile(r'0[2-478][\s-]?\d{4}[\s-]?\d{4}'),
    re.compile(r'\(\+?61\)\s?4\d{2}[\s-]?\d{3}[\s-]?\d{3}'),
    re.compile(r'\+61\s?4\d{2}\s?\d{3}\s?\d{3}'),
    re.compile(r'04\d{2}\s\d{3}\s\d{3}'),
    re.compile(r'\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),
    re.compile(r'\+\d{1,3}[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}'),
]

PHONE_CONTEXT_KEYWORDS = [
    'phone', 'mobile', 'cell', 'tel', 'contact', 'call', 'mob', 'ph'
]

REFERENCE_KEYWORDS = [
    'reference', 'referee', 'supervisor', 'manager', 'employer', 'contact person',
    'reporting to', 'reports to', 'superior', 'boss', 'hr', 'human resource'
]


def extract_email(text: str) -> Tuple[Optional[str], float, str]:
    """
    Extract first valid email address from text using regex.
    Returns: (email, confidence, method)
    """
    emails = EMAIL_PATTERN.findall(text)
    
    for email in emails:
        if any(x in email.lower() for x in ['example.com', 'test.com', 'sample.']):
            continue
        
        parts = email.split('@')
        if len(parts) == 2 and '.' in parts[1]:
            domain_parts = parts[1].split('.')
            if len(domain_parts[-1]) >= 2:
                lines = text.split('\n')
                for i, line in enumerate(lines):
                    if email.lower() in line.lower():
                        if i < 15:
                            return email, 0.95, 'regex'
                        else:
                            return email, 0.8, 'regex'
                return email, 0.85, 'regex'
    
    if emails:
        return emails[0], 0.6, 'regex'
    return None, 0.0, 'regex'


def extract_phone_candidates(text: str) -> list:
    """Extract all potential phone numbers from text."""
    candidates = []
    for pattern in PHONE_PATTERNS:
        matches = pattern.findall(text)
        for match in matches:
            phone = re.sub(r'[\s-]+', ' ', match).strip()
            if phone not in candidates:
                candidates.append(phone)
    return candidates


def is_candidate_phone(text: str, phone: str) -> Tuple[bool, float]:
    """
    Check if a phone number is likely the candidate's personal phone.
    Returns: (is_candidate, confidence)
    """
    lines = text.split('\n')
    phone_normalized = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    for i, line in enumerate(lines):
        line_normalized = re.sub(r'[\s\-\(\)\+]', '', line)
        if phone_normalized in line_normalized:
            context_start = max(0, i - 3)
            context_end = min(len(lines), i + 2)
            context = ' '.join(lines[context_start:context_end]).lower()
            
            if any(ref_kw in context for ref_kw in REFERENCE_KEYWORDS):
                return False, 0.15
            
            if i < 10:
                if any(kw in context for kw in PHONE_CONTEXT_KEYWORDS):
                    return True, 0.85
                return True, 0.7
            elif i < 15:
                return True, 0.55
                
    return True, 0.4


def extract_phone_with_context(text: str) -> Tuple[Optional[str], float, str]:
    """
    Extract phone number that is likely the candidate's own number.
    Returns: (phone, confidence, method)
    """
    candidates = extract_phone_candidates(text)
    
    best_phone = None
    best_confidence = 0.0
    
    for phone in candidates:
        is_candidate, confidence = is_candidate_phone(text, phone)
        if is_candidate and confidence > best_confidence:
            best_phone = phone
            best_confidence = confidence
    
    if best_phone:
        return best_phone, best_confidence, 'regex'
    
    return candidates[0] if candidates else None, 0.35 if candidates else 0.0, 'regex'


def extract_name_with_ai(text: str, api_key: str) -> Tuple[Optional[str], float, bool, Optional[str]]:
    """
    Extract candidate name using Claude Sonnet 4 via OpenRouter.
    Returns: (name, confidence, success, error)
    """
    if not api_key:
        return None, 0.0, False, "No API key provided"
    
    text_truncated = text[:3000] if len(text) > 3000 else text
    
    prompt = f"""Analyze this resume text and extract ONLY the candidate's full name.
The name is usually at the very top of the resume, often in a larger font or as a heading.
Do NOT include job titles, degrees, or any other text.

Resume text:
{text_truncated}

Return ONLY the candidate's full name, nothing else. If you cannot find the name, return "NOT_FOUND"."""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Resume Parser"
            },
            json={
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 100,
                "temperature": 0
            },
            timeout=30
        )
        
        if response.status_code == 402:
            return None, 0.0, False, "Insufficient AI credits"
        elif response.status_code == 429:
            return None, 0.0, False, "AI rate limit exceeded"
        elif response.status_code != 200:
            return None, 0.0, False, f"AI API error: {response.status_code}"
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
        if content and content != "NOT_FOUND":
            content = content.strip('"\'')
            if len(content) < 100 and not any(kw in content.lower() for kw in ['resume', 'cv', 'curriculum']):
                words = content.split()
                if 2 <= len(words) <= 4:
                    confidence = 0.92
                elif len(words) == 1:
                    confidence = 0.65
                else:
                    confidence = 0.55
                return content, confidence, True, None
        
        return None, 0.0, False, "Could not extract name"
            
    except requests.exceptions.Timeout:
        return None, 0.0, False, "AI request timed out"
    except requests.exceptions.RequestException as e:
        return None, 0.0, False, f"AI request failed: {str(e)}"


def extract_phone_with_ai(text: str, api_key: str, regex_phone: Optional[str] = None, 
                          regex_confidence: float = 0.0) -> Tuple[Optional[str], float, bool, Optional[str]]:
    """
    Extract/validate candidate's phone number using Claude Sonnet 4.
    Returns: (phone, confidence, ai_used, error)
    """
    if not api_key:
        return regex_phone, regex_confidence, False, None
    
    text_truncated = text[:3000] if len(text) > 3000 else text
    
    prompt = f"""Analyze this resume text and extract ONLY the candidate's personal phone number.

IMPORTANT: 
- Extract the candidate's OWN phone number, NOT their reference's, supervisor's, or previous employer's phone
- The candidate's phone is usually at the top of the resume in the contact section
- Ignore any phone numbers in the "References" section or next to reference names
- Return the phone number in its original format

Resume text:
{text_truncated}

Return ONLY the candidate's phone number, nothing else. If you cannot find it or are unsure, return "NOT_FOUND"."""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "X-Title": "Resume Parser"
            },
            json={
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 50,
                "temperature": 0
            },
            timeout=30
        )
        
        if response.status_code == 402:
            return regex_phone, regex_confidence, False, "Insufficient AI credits"
        elif response.status_code == 429:
            return regex_phone, regex_confidence, False, "AI rate limit exceeded"
        elif response.status_code != 200:
            return regex_phone, regex_confidence, False, f"AI API error: {response.status_code}"
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
        
        if content and content != "NOT_FOUND":
            content = content.strip('"\'')
            phone_match = re.search(r'[\d\s\-\+\(\)]{8,}', content)
            if phone_match:
                ai_phone = phone_match.group(0).strip()
                if regex_phone:
                    regex_normalized = re.sub(r'[\s\-\(\)\+]', '', regex_phone)
                    ai_normalized = re.sub(r'[\s\-\(\)\+]', '', ai_phone)
                    if regex_normalized == ai_normalized:
                        return regex_phone, 0.95, True, None
                    else:
                        return ai_phone, 0.88, True, None
                return ai_phone, 0.88, True, None
        
        if regex_phone:
            return regex_phone, regex_confidence, False, None
        
        return None, 0.0, False, None
            
    except requests.exceptions.Timeout:
        return regex_phone, regex_confidence, False, "AI request timed out"
    except requests.exceptions.RequestException as e:
        return regex_phone, regex_confidence, False, f"AI request failed: {str(e)}"


def check_ai_credits(api_key: str) -> Tuple[bool, Optional[str]]:
    """Check if the API key has available credits."""
    if not api_key:
        return False, "No API key configured"
    
    try:
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={
                "Authorization": f"Bearer {api_key}",
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            limit = data.get('data', {}).get('limit')
            usage = data.get('data', {}).get('usage', 0)
            
            if limit is not None and usage >= limit:
                return False, "AI credit limit reached"
            
            return True, None
        elif response.status_code == 401:
            return False, "Invalid API key"
        else:
            return True, None
            
    except:
        return True, None


def process_resume(text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Process resume text with confidence scores:
    - Always use AI for name extraction
    - Use regex for email (always)
    - Use regex + AI validation for phone numbers
    """
    result = {
        'name': None,
        'email': None,
        'phone': None,
        'ai_used': False,
        'error': None,
        'confidence': {
            'name': 0.0,
            'email': 0.0,
            'phone': 0.0
        },
        'methods': {
            'name': 'none',
            'email': 'regex',
            'phone': 'none'
        }
    }
    
    email, email_confidence, email_method = extract_email(text)
    result['email'] = email
    result['confidence']['email'] = email_confidence
    result['methods']['email'] = email_method
    
    regex_phone, phone_confidence, phone_method = extract_phone_with_context(text)
    
    if api_key:
        name, name_confidence, name_success, name_error = extract_name_with_ai(text, api_key)
        if name_success:
            result['name'] = name
            result['confidence']['name'] = name_confidence
            result['methods']['name'] = 'ai'
            result['ai_used'] = True
        elif name_error and 'credit' in name_error.lower():
            result['error'] = name_error
        
        phone, phone_conf, phone_ai_used, phone_error = extract_phone_with_ai(
            text, api_key, regex_phone, phone_confidence
        )
        result['phone'] = phone
        result['confidence']['phone'] = phone_conf
        
        if phone_ai_used:
            result['methods']['phone'] = 'ai'
            result['ai_used'] = True
        else:
            result['methods']['phone'] = 'regex'
            
        if phone_error and not result['error']:
            result['error'] = phone_error
    else:
        result['phone'] = regex_phone
        result['confidence']['phone'] = phone_confidence
        result['methods']['phone'] = phone_method
        result['error'] = "No API key - using regex only"
    
    return result

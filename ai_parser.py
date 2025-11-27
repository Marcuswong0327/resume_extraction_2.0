"""
AI Parser Module
Uses regex patterns first, then falls back to OpenRouter Claude Sonnet
for extraction when regex fails.
"""

import re
import os
import requests
from typing import Optional, Dict, Any, Tuple


# Regex Patterns
EMAIL_PATTERN = re.compile(
    r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    re.IGNORECASE
)

# Australian phone patterns - flexible to handle various formats
# Matches: +61 412 345 678, 0412 345 678, 0412-345-678, 04 1234 5678, etc.
PHONE_PATTERNS = [
    # +61 format with various separators
    re.compile(r'\+61\s?[2-478](?:\s?-?\d){8}'),
    # 04xx format (mobile)
    re.compile(r'0[45]\d{2}[\s-]?\d{3}[\s-]?\d{3}'),
    # General Australian format
    re.compile(r'(?:\+?61|0)\s?[2-478](?:[\s-]?\d){8}'),
    # Compact format
    re.compile(r'04\d{8}'),
    # With country code in parentheses
    re.compile(r'\(\+?61\)\s?[2-478](?:[\s-]?\d){8}'),
    # Format like: 0435 860 589 or 0416 851 877
    re.compile(r'0[2-478]\d{2}\s\d{3}\s\d{3}'),
    # Format with dots: 0412.345.678
    re.compile(r'0[2-478]\d{2}[.\s-]?\d{3}[.\s-]?\d{3}'),
]

# Words to skip when looking for names
SKIP_WORDS = {
    'resume', 'cv', 'curriculum', 'vitae', 'profile', 'summary',
    'objective', 'experience', 'education', 'skills', 'contact',
    'phone', 'email', 'address', 'mobile', 'tel', 'linkedin',
    'github', 'portfolio', 'website', 'references', 'personal',
    'professional', 'career', 'work', 'employment', 'history'
}


def extract_email(text: str) -> Optional[str]:
    """Extract first email address from text."""
    match = EMAIL_PATTERN.search(text)
    return match.group(0) if match else None


def extract_phone(text: str) -> Optional[str]:
    """Extract first phone number from text using multiple patterns."""
    for pattern in PHONE_PATTERNS:
        match = pattern.search(text)
        if match:
            # Clean up the phone number
            phone = match.group(0)
            # Normalize spaces
            phone = re.sub(r'[\s-]+', ' ', phone).strip()
            return phone
    return None


def extract_name(text: str) -> Optional[str]:
    """
    Extract candidate name using heuristics.
    Name is usually the first prominent text in a resume.
    """
    lines = text.split('\n')
    
    for line in lines[:10]:  # Check first 10 lines
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Skip lines with common section headers
        lower_line = line.lower()
        if any(skip in lower_line for skip in SKIP_WORDS):
            continue
        
        # Skip lines with email or phone
        if '@' in line or re.search(r'\d{4,}', line):
            continue
        
        # Skip lines that are too long (likely descriptions)
        if len(line) > 50:
            continue
        
        # Check if line looks like a name (2-4 capitalized words)
        words = line.split()
        if 1 <= len(words) <= 4:
            # Check if words look like names (capitalized, alphabetic)
            if all(word[0].isupper() and word.replace('-', '').replace("'", '').isalpha() 
                   for word in words if len(word) > 1):
                return line
    
    return None


def extract_with_regex(text: str) -> Dict[str, Optional[str]]:
    """
    Extract name, email, and phone using regex patterns.
    
    Returns:
        Dictionary with 'name', 'email', 'phone' keys
    """
    return {
        'name': extract_name(text),
        'email': extract_email(text),
        'phone': extract_phone(text)
    }


def extract_with_ai(text: str, api_key: str) -> Tuple[Dict[str, Optional[str]], bool, Optional[str]]:
    """
    Extract information using OpenRouter Claude Sonnet API.
    
    Args:
        text: Resume text to analyze
        api_key: OpenRouter API key
        
    Returns:
        Tuple of (extracted_data, success, error_message)
    """
    if not api_key:
        return {}, False, "No API key provided"
    
    # Truncate text to avoid token limits
    text_truncated = text[:4000] if len(text) > 4000 else text
    
    prompt = f"""Analyze this resume text and extract the following information. 
Return ONLY a JSON object with these exact keys: "name", "email", "phone"
If any field cannot be found, use null for that field.

Resume text:
{text_truncated}

Return ONLY the JSON object, no other text."""

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {CLAUDE_SONNET_API_KEY}",
                "Content-Type": "application/json",
                "X-Title": "Resume Parser"
            },
            json={
                "model": "anthropic/claude-sonnet-4",
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 500,
                "temperature": 0
            },
            timeout=30
        )
        
        # Check for credit/rate limit errors
        if response.status_code == 402:
            return {}, False, "Insufficient AI credits"
        elif response.status_code == 429:
            return {}, False, "AI rate limit exceeded"
        elif response.status_code != 200:
            return {}, False, f"AI API error: {response.status_code}"
        
        result = response.json()
        content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        
        # Parse JSON from response
        import json
        # Try to extract JSON from the response
        try:
            # Handle case where response has markdown code blocks
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
            # Try to extract with regex as fallback
            return {}, False, "Failed to parse AI response"
            
    except requests.exceptions.Timeout:
        return {}, False, "AI request timed out"
    except requests.exceptions.RequestException as e:
        return {}, False, f"AI request failed: {str(e)}"


def check_ai_credits(api_key: str) -> Tuple[bool, Optional[str]]:
    """
    Check if the API key has available credits.
    
    Returns:
        Tuple of (has_credits, error_message)
    """
    if not api_key:
        return False, "No API key configured"
    
    try:
        # Make a minimal request to check credits
        response = requests.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={
                "Authorization": f"Bearer {CLAUDE_SONNET_API_KEY}",
            },
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            # Check if there are remaining credits
            limit = data.get('data', {}).get('limit')
            usage = data.get('data', {}).get('usage', 0)
            
            if limit is not None and usage >= limit:
                return False, "AI credit limit reached"
            
            return True, None
        elif response.status_code == 401:
            return False, "Invalid API key"
        else:
            return True, None  # Assume has credits if we can't check
            
    except:
        return True, None  # Assume has credits if check fails


def process_resume(text: str, api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Process resume text: try regex first, fallback to AI if needed.
    
    Args:
        text: Resume text
        api_key: Optional OpenRouter API key for AI fallback
        
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
    
    # Step 1: Try regex extraction
    regex_result = extract_with_regex(text)
    result.update(regex_result)
    
    # Step 2: If any field is missing, try AI
    missing_fields = [k for k in ['name', 'email', 'phone'] if not result[k]]
    
    if missing_fields and api_key:
        ai_result, success, error = extract_with_ai(text, api_key)
        
        if success:
            result['ai_used'] = True
            # Fill in missing fields from AI
            for field in missing_fields:
                if ai_result.get(field):
                    result[field] = ai_result[field]
        elif error:
            result['error'] = error
    
    return result

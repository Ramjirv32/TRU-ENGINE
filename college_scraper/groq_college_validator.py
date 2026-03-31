import requests
import json
from typing import Dict, Optional

GROQ_API_KEY = "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"
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"


class CollegeValidator:
    """Validates and corrects college names using Groq API"""

    @staticmethod
    def validate(college_name: str, country: str = "Unknown", city: str = "Unknown") -> Dict:
        """
        Validate and correct a college name using Groq
        
        Args:
            college_name: Name entered by user
            country: Country (optional)
            city: City (optional)
            
        Returns:
            {
                "name": "Corrected Full College Name",
                "country": "Exact Country",
                "location": "Exact City",
                "is_valid": True/False,
                "error": "Error message if validation failed"
            }
        """
        if not college_name or not college_name.strip():
            return {
                "is_valid": False,
                "error": "College name is required"
            }

        try:
            # Build prompt
            prompt = CollegeValidator._build_prompt(college_name, country, city)
            
            # Call Groq API
            groq_response = CollegeValidator._call_groq_api(prompt)
            
            # Parse response
            validated = CollegeValidator._parse_response(groq_response)
            return validated
            
        except Exception as e:
            print(f"❌ Groq validation error: {e}")
            return {
                "is_valid": False,
                "error": str(e)
            }

    @staticmethod
    def _build_prompt(college_name: str, country: str, city: str) -> str:
        """Build the validation prompt for Groq"""
        return f"""You are a college/university name validator.
        
User entered:
- College Name: {college_name}
- Country: {country}
- City: {city}

Your task:
1. Identify the correct full name of this college/university
2. Provide the exact country name
3. Provide the exact city/location

IMPORTANT: Reply ONLY with valid JSON (no markdown, no code blocks, no extra text):
{{"name": "Full Official College Name", "country": "Exact Country Name", "location": "Exact City Name", "found": true}}

If the college cannot be found or validated, reply:
{{"name": "N/A", "country": "N/A", "location": "N/A", "found": false}}"""

    @staticmethod
    def _call_groq_api(prompt: str) -> str:
        """Call Groq API and return response content"""
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "model": GROQ_MODEL,
            "temperature": 0.3,
            "max_completion_tokens": 256,
            "top_p": 1.0
        }
        
        response = requests.post(GROQ_BASE_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if "choices" not in data or len(data["choices"]) == 0:
            raise Exception("No response from Groq API")
        
        return data["choices"][0]["message"]["content"]

    @staticmethod
    def _parse_response(groq_response: str) -> Dict:
        """Parse Groq's JSON response"""
        try:
            # Clean response - remove markdown code blocks if present
            groq_response = groq_response.strip()
            if groq_response.startswith("```json"):
                groq_response = groq_response[7:]
            if groq_response.startswith("```"):
                groq_response = groq_response[3:]
            if groq_response.endswith("```"):
                groq_response = groq_response[:-3]
            groq_response = groq_response.strip()
            
            # Parse JSON
            parsed = json.loads(groq_response)
            
            # Extract fields
            name = parsed.get("name", "").strip()
            country = parsed.get("country", "").strip()
            location = parsed.get("location", "").strip()
            found = parsed.get("found", False)
            
            # Validate
            if not found or name == "N/A" or country == "N/A":
                return {
                    "is_valid": False,
                    "error": "College not found in validation"
                }
            
            return {
                "is_valid": True,
                "name": name,
                "country": country,
                "location": location
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️  Failed to parse Groq JSON response: {e}")
            print(f"Raw response: {groq_response[:200]}")
            return {
                "is_valid": False,
                "error": f"Invalid response from validation: {str(e)}"
            }


# Convenience function
def validate_college_name(college_name: str, country: str = "Unknown", city: str = "Unknown") -> Dict:
    """Validate college name using Groq"""
    return CollegeValidator.validate(college_name, country, city)

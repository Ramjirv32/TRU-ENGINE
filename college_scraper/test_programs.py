import json
import subprocess
import os
import re

def test_programs_query():
    """Test UG programs query for University of Rwanda"""
    
    # Test University of Rwanda - UG programs only
    query = "List all available undergraduate programs offered at University of Rwanda. Include all bachelor degree programs, faculties, and their specializations."
    
    api_key = "918d9970ddb395770566bba8b2d0ef4f25b8da926652ae908a52894392c752b0"
    
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={query}",
        "--data-urlencode", f"api_key={api_key}",
        "--silent"
    ]
    
    print("🔍 Testing University of Rwanda UG programs query...")
    print(f"Query: {query}")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ API Response received:")
            print(result.stdout)
            
            # Try to parse and analyze the response
            try:
                data = json.loads(result.stdout)
                print("\n📊 Response Analysis:")
                print(f"Keys in response: {list(data.keys())}")
                
                if "reconstructed_markdown" in data:
                    content = data["reconstructed_markdown"]
                    print(f"✅ Has reconstructed_markdown! Length: {len(content)}")
                    print(f"Content preview: {content[:500]}...")
                    
                    # Count UG programs specifically
                    ug_count = content.lower().count("bachelor") + content.lower().count("b.sc") + content.lower().count("b.a") + content.lower().count("bba") + content.lower().count("bcom") + content.lower().count("undergraduate")
                    
                    print(f"🎓 UG course mentions detected: {ug_count}")
                    
                    # Extract specific UG courses
                    ug_courses = []
                    
                    # Bachelor degree programs
                    bachelor_pattern = r'Bachelor(?:\'s)?\s+(?:of\s+)?([A-Za-z\s]+)(?:\s+in\s+([^\n-]+))?'
                    bachelor_matches = re.findall(bachelor_pattern, content, re.IGNORECASE)
                    for match in bachelor_matches:
                        if match[1]:
                            ug_courses.append(f"Bachelor of {match[0].strip()} in {match[1].strip()}")
                        else:
                            ug_courses.append(f"Bachelor of {match[0].strip()}")
                    
                    # B.Sc programs
                    bsc_pattern = r'B\.?[Ss][Cc]\.?\s+(?:in\s+)?([^\n-]+)'
                    bsc_matches = re.findall(bsc_pattern, content, re.IGNORECASE)
                    ug_courses.extend([f"B.Sc {match.strip()}" for match in bsc_matches])
                    
                    # B.A programs
                    ba_pattern = r'B\.?[Aa]\.?\s+(?:in\s+)?([^\n-]+)'
                    ba_matches = re.findall(ba_pattern, content, re.IGNORECASE)
                    ug_courses.extend([f"B.A {match.strip()}" for match in ba_matches])
                    
                    # BBA programs
                    if "bba" in content.lower():
                        ug_courses.append("BBA")
                    
                    # BCom programs
                    if "bcom" in content.lower() or "b.com" in content.lower():
                        ug_courses.append("B.Com")
                    
                    # Look for faculty/college mentions
                    faculty_pattern = r'(?:Faculty|College|School)\s+of\s+([^\n-]+)'
                    faculty_matches = re.findall(faculty_pattern, content, re.IGNORECASE)
                    
                    print(f"\n🎓 EXTRACTED UG COURSES ({len(ug_courses)}):")
                    for i, course in enumerate(sorted(set(ug_courses)), 1):
                        print(f"   {i}. {course}")
                    
                    print(f"\n🏛️ FACULTIES/COLLEGES DETECTED ({len(faculty_matches)}):")
                    for i, faculty in enumerate(sorted(set(faculty_matches)), 1):
                        print(f"   {i}. {faculty.strip()}")
                    
                else:
                    print("❌ No reconstructed_markdown found")
                
                if "answer_box" in data:
                    print("✅ Has answer_box!")
                    
                if "organic_results" in data:
                    print(f"✅ Has organic_results: {len(data['organic_results'])}")
                    
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
                
        else:
            print(f"❌ API Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_programs_query()

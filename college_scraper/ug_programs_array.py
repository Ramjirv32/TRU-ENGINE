import json
import subprocess
import re

def get_ug_programs_array():
    """Extract all UG programs from University of Rwanda and return as array"""
    
    query = "List all available undergraduate programs offered at University of Rwanda 130 programs. "
    
    api_key = "918d9970ddb395770566bba8b2d0ef4f25b8da926652ae908a52894392c752b0"
    
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={query}",
        "--data-urlencode", f"api_key={api_key}",
        "--silent"
    ]
    
    print("🔍 Extracting UG programs from University of Rwanda...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if "reconstructed_markdown" in data:
                content = data["reconstructed_markdown"]
                
                ug_programs = []
                
                # Extract BSc (Hons) programs
                bsc_hons_pattern = r'BSc\s*\(Hons\)\s*in\s*([^\n-]+)'
                bsc_matches = re.findall(bsc_hons_pattern, content, re.IGNORECASE)
                for match in bsc_matches:
                    clean_match = match.strip()
                    if clean_match and len(clean_match) > 3:
                        ug_programs.append(f"BSc (Hons) in {clean_match}")
                
                # Extract Bachelor of programs
                bachelor_pattern = r'Bachelor\s+of\s+([^\n-]+)'
                bachelor_matches = re.findall(bachelor_pattern, content, re.IGNORECASE)
                for match in bachelor_matches:
                    clean_match = match.strip()
                    if clean_match and len(clean_match) > 3 and "programs" not in clean_match.lower():
                        ug_programs.append(f"Bachelor of {clean_match}")
                
                # Extract other BSc programs
                bsc_pattern = r'BSc\s+with\s+Honours\s+in\s*([^\n,]+)'
                bsc_matches2 = re.findall(bsc_pattern, content, re.IGNORECASE)
                for match in bsc_matches2:
                    clean_match = match.strip()
                    if clean_match and len(clean_match) > 3:
                        ug_programs.append(f"BSc with Honours in {clean_match}")
                
                # Clean and unique programs
                ug_programs = list(set([prog.strip() for prog in ug_programs if len(prog.strip()) > 10]))
                ug_programs.sort()
                
                print("🎓 ALL UG PROGRAMS AT UNIVERSITY OF RWANDA:")
                print("=" * 60)
                
                # Display as array format
                print("ug_programs = [")
                for i, program in enumerate(ug_programs):
                    comma = "," if i < len(ug_programs) - 1 else ""
                    print(f'    "{program}"{comma}')
                print("]")
                
                print(f"\n📊 Total UG Programs: {len(ug_programs)}")
                
                return ug_programs
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return []

if __name__ == "__main__":
    programs = get_ug_programs_array()

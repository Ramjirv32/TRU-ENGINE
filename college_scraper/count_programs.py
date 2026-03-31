import json
import subprocess
import os
import re

def count_programs_detailed():
    """Count exact number of programs and departments for NIT Trichy"""
    
    query = "What are the main academic programs offered at NIT Trichy (National Institute of Technology Tiruchirappalli) in India? List the undergraduate, postgraduate, and PhD programs available. Also list the main academic departments."
    
    api_key = "918d9970ddb395770566bba8b2d0ef4f25b8da926652ae908a52894392c752b0"
    
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={query}",
        "--data-urlencode", f"api_key={api_key}",
        "--silent"
    ]
    
    print("🔍 Analyzing NIT Trichy programs and departments...")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if "reconstructed_markdown" in data:
                content = data["reconstructed_markdown"]
                print(f"📄 Total content length: {len(content)} characters")
                print("\n" + "="*80)
                
                # Extract UG Programs
                print("\n🎓 UNDERGRADUATE PROGRAMS:")
                ug_programs = []
                
                # Look for B.Tech programs
                btech_pattern = r'B\.?[Tt]ech\.?\s+in\s+([^\n-]+)'
                btech_matches = re.findall(btech_pattern, content, re.IGNORECASE)
                ug_programs.extend([f"B.Tech {match.strip()}" for match in btech_matches])
                
                # Look for B.E programs
                be_pattern = r'B\.?[Ee]\.?\s+in\s+([^\n-]+)'
                be_matches = re.findall(be_pattern, content, re.IGNORECASE)
                ug_programs.extend([f"B.E {match.strip()}" for match in be_matches])
                
                # Look for B.Arch programs
                arch_pattern = r'B\.?[Aa]rch\.?\s+([^\n-]*)'
                arch_matches = re.findall(arch_pattern, content, re.IGNORECASE)
                ug_programs.extend([f"B.Arch {match.strip()}" for match in arch_matches])
                
                # Look for B.Sc programs
                bsc_pattern = r'B\.?[Ss][Cc]\.?\s+in\s+([^\n-]+)'
                bsc_matches = re.findall(bsc_pattern, content, re.IGNORECASE)
                ug_programs.extend([f"B.Sc {match.strip()}" for match in bsc_matches])
                
                # Clean and unique UG programs
                ug_programs = list(set([prog.strip() for prog in ug_programs if len(prog.strip()) > 8]))
                for i, prog in enumerate(sorted(ug_programs), 1):
                    print(f"   {i}. {prog}")
                
                # Extract PG Programs
                print(f"\n📚 POSTGRADUATE PROGRAMS:")
                pg_programs = []
                
                # Look for M.Tech programs
                mtech_pattern = r'M\.?[Tt]ech\.?\s+in\s+([^\n-]+)'
                mtech_matches = re.findall(mtech_pattern, content, re.IGNORECASE)
                pg_programs.extend([f"M.Tech {match.strip()}" for match in mtech_matches])
                
                # Look for M.E programs
                me_pattern = r'M\.?[Ee]\.?\s+in\s+([^\n-]+)'
                me_matches = re.findall(me_pattern, content, re.IGNORECASE)
                pg_programs.extend([f"M.E {match.strip()}" for match in me_matches])
                
                # Look for MBA programs
                mba_pattern = r'MBA\s+([^\n-]*)'
                mba_matches = re.findall(mba_pattern, content, re.IGNORECASE)
                pg_programs.extend([f"MBA {match.strip()}" for match in mba_matches])
                
                # Look for M.Sc programs
                msc_pattern = r'M\.?[Ss][Cc]\.?\s+in\s+([^\n-]+)'
                msc_matches = re.findall(msc_pattern, content, re.IGNORECASE)
                pg_programs.extend([f"M.Sc {match.strip()}" for match in msc_matches])
                
                # Look for M.Arch programs
                march_pattern = r'M\.?[Aa]rch\.?\s+([^\n-]*)'
                march_matches = re.findall(march_pattern, content, re.IGNORECASE)
                pg_programs.extend([f"M.Arch {match.strip()}" for match in march_matches])
                
                # Clean and unique PG programs
                pg_programs = list(set([prog.strip() for prog in pg_programs if len(prog.strip()) > 8]))
                for i, prog in enumerate(sorted(pg_programs), 1):
                    print(f"   {i}. {prog}")
                
                # Extract PhD Programs
                print(f"\n🔬 PhD PROGRAMS:")
                phd_programs = []
                
                # Look for PhD programs
                phd_pattern = r'PhD\s+in\s+([^\n-]+)'
                phd_matches = re.findall(phd_pattern, content, re.IGNORECASE)
                phd_programs.extend([f"PhD {match.strip()}" for match in phd_matches])
                
                # Look for Doctoral programs
                doctoral_pattern = r'Doctoral\s+([^\n-]+)'
                doctoral_matches = re.findall(doctoral_pattern, content, re.IGNORECASE)
                phd_programs.extend([f"Doctoral {match.strip()}" for match in doctoral_matches])
                
                # Clean and unique PhD programs
                phd_programs = list(set([prog.strip() for prog in phd_programs if len(prog.strip()) > 8]))
                for i, prog in enumerate(sorted(phd_programs), 1):
                    print(f"   {i}. {prog}")
                
                # Extract Departments
                print(f"\n🏛️ ACADEMIC DEPARTMENTS:")
                departments = []
                
                # Look for department patterns
                dept_patterns = [
                    r'(?:Department of|Dept\. of)\s+([^\n,]+)',
                    r'([A-Za-z\s]+(?:Engineering|Science|Technology|Management|Studies|Computer|Electrical|Mechanical|Civil|Architecture|Mathematics|Physics|Chemistry|Humanities)\s+Department)',
                    r'([A-Za-z\s]+(?:Engineering|Science|Technology|Management|Computer|Electrical|Mechanical|Civil|Architecture|Mathematics|Physics|Chemistry|Humanities)\s+Dept\.?)',
                ]
                
                for pattern in dept_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    departments.extend(matches)
                
                # Clean and unique departments
                departments = list(set([dept.strip() for dept in departments if len(dept.strip()) > 3]))
                for i, dept in enumerate(sorted(departments), 1):
                    print(f"   {i}. {dept}")
                
                # Summary
                print("\n" + "="*80)
                print("📊 SUMMARY COUNTS:")
                print(f"   🎓 Undergraduate Programs: {len(ug_programs)}")
                print(f"   📚 Postgraduate Programs: {len(pg_programs)}")
                print(f"   🔬 PhD Programs: {len(phd_programs)}")
                print(f"   🏛️ Academic Departments: {len(departments)}")
                print(f"   📈 Total Programs: {len(ug_programs) + len(pg_programs) + len(phd_programs)}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    count_programs_detailed()

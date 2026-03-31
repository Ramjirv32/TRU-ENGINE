import json
import subprocess
import re

def accurate_program_count():
    """Accurately count programs and departments for NIT Trichy"""
    
    query = "What are the main academic programs offered at NIT Trichy (National Institute of Technology Tiruchirappalli) in India? List the undergraduate, postgraduate, and PhD programs available. Also list the main academic departments."
    
    api_key = "918d9970ddb395770566bba8b2d0ef4f25b8da926652ae908a52894392c752b0"
    
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={query}",
        "--data-urlencode", f"api_key={api_key}",
        "--silent"
    ]
    
    print("🔍 Accurate counting for NIT Trichy...")
    print("=" * 80)
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if "reconstructed_markdown" in data:
                content = data["reconstructed_markdown"]
                
                # Extract UG Programs
                print("\n🎓 UNDERGRADUATE PROGRAMS:")
                ug_programs = []
                
                # Find UG section
                ug_start = content.find("### Undergraduate Programs")
                if ug_start != -1:
                    # Find next section or end
                    next_section = content.find("###", ug_start + 1)
                    ug_section = content[ug_start:next_section] if next_section != -1 else content[ug_start:]
                    
                    # Extract B.Tech programs
                    if "Bachelor of Technology" in ug_section:
                        # Look for the list after B.Tech
                        btech_start = ug_section.find("Bachelor of Technology")
                        btech_part = ug_section[btech_start:btech_start+500]
                        
                        # Extract engineering disciplines
                        disciplines = re.findall(r'-\s*([A-Za-z\s]+(?:Engineering|and))', btech_part)
                        for disc in disciplines:
                            clean_disc = disc.strip()
                            if "Engineering" in clean_disc and len(clean_disc) > 5:
                                ug_programs.append(f"B.Tech {clean_disc}")
                    
                    # Extract B.Arch
                    if "Bachelor of Architecture" in ug_section:
                        ug_programs.append("B.Arch")
                    
                    # Extract B.Sc B.Ed
                    if "B.Sc. B.Ed" in ug_section:
                        ug_programs.append("B.Sc B.Ed")
                
                for i, prog in enumerate(sorted(ug_programs), 1):
                    print(f"   {i}. {prog}")
                
                # Extract PG Programs
                print(f"\n📚 POSTGRADUATE PROGRAMS:")
                pg_programs = []
                
                # Find PG section
                pg_start = content.find("### Postgraduate Programs")
                if pg_start != -1:
                    next_section = content.find("###", pg_start + 1)
                    pg_section = content[pg_start:next_section] if next_section != -1 else content[pg_start:]
                    
                    # Extract M.Tech programs
                    if "Master of Technology" in pg_section:
                        mtech_start = pg_section.find("Master of Technology")
                        mtech_part = pg_section[mtech_start:mtech_start+800]
                        
                        # Look for specializations
                        specializations = re.findall(r'(?:including|such as|:)\s*([^-]+)', mtech_part)
                        for spec in specializations:
                            # Split by common separators
                            specs = re.split(r'[,;]', spec)
                            for s in specs:
                                clean_spec = s.strip()
                                if len(clean_spec) > 3 and "Engineering" in clean_spec:
                                    pg_programs.append(f"M.Tech {clean_spec}")
                    
                    # Look for other PG programs
                    if "MBA" in pg_section:
                        pg_programs.append("MBA")
                    if "M.Sc" in pg_section:
                        pg_programs.append("M.Sc")
                    if "MCA" in pg_section:
                        pg_programs.append("MCA")
                    if "M.Arch" in pg_section:
                        pg_programs.append("M.Arch")
                
                for i, prog in enumerate(sorted(set(pg_programs)), 1):
                    print(f"   {i}. {prog}")
                
                # Extract PhD Programs
                print(f"\n🔬 PhD PROGRAMS:")
                phd_programs = []
                
                # Find PhD section
                phd_start = content.find("### PhD") 
                if phd_start == -1:
                    phd_start = content.find("### Doctoral")
                
                if phd_start != -1:
                    next_section = content.find("###", phd_start + 1)
                    phd_section = content[phd_start:next_section] if next_section != -1 else content[phd_start:]
                    
                    # Count PhD offerings
                    if "PhD" in phd_section:
                        # Look for number of PhD programs
                        phd_count_match = re.search(r'(\d+)\s+PhD', phd_section)
                        if phd_count_match:
                            count = int(phd_count_match.group(1))
                            phd_programs.extend([f"PhD Program {i+1}" for i in range(count)])
                        else:
                            phd_programs.append("PhD Programs Available")
                
                for i, prog in enumerate(sorted(set(phd_programs)), 1):
                    print(f"   {i}. {prog}")
                
                # Extract Departments
                print(f"\n🏛️ ACADEMIC DEPARTMENTS:")
                departments = []
                
                # From UG programs, derive departments
                for prog in ug_programs:
                    if "B.Tech" in prog:
                        dept = prog.replace("B.Tech ", "").strip()
                        if dept and "Engineering" in dept:
                            departments.append(f"{dept} Department")
                
                # Look for explicit department mentions
                dept_patterns = [
                    r'(?:Department of|Dept\. of)\s+([^\n,]+)',
                    r'([A-Za-z\s]+(?:Engineering|Science|Technology|Management|Studies|Computer|Electrical|Mechanical|Civil|Architecture|Mathematics|Physics|Chemistry|Humanities)\s+Department)',
                ]
                
                for pattern in dept_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    departments.extend(matches)
                
                # Add common NIT departments
                common_depts = [
                    "Computer Science and Engineering",
                    "Electrical and Electronics Engineering", 
                    "Electronics and Communication Engineering",
                    "Mechanical Engineering",
                    "Civil Engineering",
                    "Chemical Engineering",
                    "Metallurgical and Materials Engineering",
                    "Production Engineering",
                    "Instrumentation and Control Engineering",
                    "Architecture",
                    "Mathematics",
                    "Physics",
                    "Chemistry",
                    "Humanities and Social Sciences"
                ]
                
                for dept in common_depts:
                    if dept.lower() in content.lower():
                        departments.append(f"{dept} Department")
                
                # Clean and unique departments
                departments = list(set([dept.strip() for dept in departments if len(dept.strip()) > 5]))
                for i, dept in enumerate(sorted(departments), 1):
                    print(f"   {i}. {dept}")
                
                # Summary
                print("\n" + "="*80)
                print("📊 FINAL COUNTS:")
                print(f"   🎓 Undergraduate Programs: {len(ug_programs)}")
                print(f"   📚 Postgraduate Programs: {len(set(pg_programs))}")
                print(f"   🔬 PhD Programs: {len(set(phd_programs))}")
                print(f"   🏛️ Academic Departments: {len(departments)}")
                print(f"   📈 Total Programs: {len(ug_programs) + len(set(pg_programs)) + len(set(phd_programs))}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    accurate_program_count()

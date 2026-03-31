import json
import subprocess
import re

def check_content_format():
    """Check the actual format of NIT Trichy content"""
    
    query = "What are the main academic programs offered at NIT Trichy (National Institute of Technology Tiruchirappalli) in India? List the undergraduate, postgraduate, and PhD programs available. Also list the main academic departments."
    
    api_key = "918d9970ddb395770566bba8b2d0ef4f25b8da926652ae908a52894392c752b0"
    
    cmd = [
        "curl", "--get", "https://serpapi.com/search",
        "--data-urlencode", "engine=google_ai_mode",
        "--data-urlencode", f"q={query}",
        "--data-urlencode", f"api_key={api_key}",
        "--silent"
    ]
    
    print("🔍 Checking NIT Trichy content format...")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            if "reconstructed_markdown" in data:
                content = data["reconstructed_markdown"]
                
                # Show first 1000 characters to understand format
                print("📄 First 1000 characters:")
                print("-" * 60)
                print(content[:1000])
                print("-" * 60)
                
                # Look for program patterns manually
                print("\n🔍 Manual pattern search:")
                
                # Check for different program listing patterns
                if "### Undergraduate" in content:
                    print("✅ Found '### Undergraduate' section")
                    ug_start = content.find("### Undergraduate")
                    ug_section = content[ug_start:ug_start+1000]
                    print("UG section preview:")
                    print(ug_section[:500])
                
                if "### Postgraduate" in content:
                    print("✅ Found '### Postgraduate' section")
                    pg_start = content.find("### Postgraduate")
                    pg_section = content[pg_start:pg_start+1000]
                    print("PG section preview:")
                    print(pg_section[:500])
                
                if "### PhD" in content or "### Doctoral" in content:
                    print("✅ Found PhD/Doctoral section")
                
                # Look for bullet points
                bullet_points = re.findall(r'^\s*[-*]\s+(.+)$', content, re.MULTILINE)
                print(f"\n📝 Found {len(bullet_points)} bullet points:")
                for i, point in enumerate(bullet_points[:10], 1):
                    print(f"   {i}. {point.strip()}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    check_content_format()

import json
import redis

def fetch_from_redis_and_create_html():
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Get all keys that match our pattern
    keys = r.keys('*_university_*')
    colleges_data = {}
    
    for key in keys:
        key_str = key.decode('utf-8')
        data = r.get(key)
        if data:
            college_data = json.loads(data.decode('utf-8'))
            colleges_data[key_str] = college_data
            print(f"✓ Fetched from Redis: {key_str}")
    
    # Create HTML
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>College Database</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .header { text-align: center; margin-bottom: 30px; }
        .college { background: white; margin: 20px 0; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        .college-name { color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; margin-bottom: 20px; font-size: 24px; }
        .section { margin: 15px 0; }
        .section-title { color: #3498db; font-weight: bold; font-size: 18px; margin-bottom: 10px; }
        .data-field { margin: 8px 0; padding: 8px; background: #ecf0f1; border-radius: 4px; }
        .field-label { font-weight: bold; color: #555; }
        .field-value { color: #2c3e50; }
        .programs-list, .placements-list { list-style: none; padding: 0; }
        .programs-list li, .placements-list li { background: #e8f6f3; margin: 5px 0; padding: 10px; border-radius: 4px; }
        .error { color: #e74c3c; background: #fadbd8; padding: 10px; border-radius: 4px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎓 College Database</h1>
        <p>Complete college information fetched from Redis database</p>
    </div>
"""
    
    for key, college in colleges_data.items():
        html_content += f"""
    <div class="college">
        <div class="college-name">{college.get('college_name', 'Unknown College')}</div>
        
        <div class="section">
            <div class="section-title">📋 Basic Information</div>
            <div class="data-field">
                <span class="field-label">Country:</span> 
                <span class="field-value">{college.get('basic_info', {}).get('country', 'N/A')}</span>
            </div>
            <div class="data-field">
                <span class="field-label">Location:</span> 
                <span class="field-value">{college.get('basic_info', {}).get('location', 'N/A')}</span>
            </div>
            <div class="data-field">
                <span class="field-label">Established:</span> 
                <span class="field-value">{college.get('basic_info', {}).get('established', 'N/A')}</span>
            </div>
            <div class="data-field">
                <span class="field-label">Website:</span> 
                <span class="field-value"><a href="{college.get('basic_info', {}).get('website', '#')}" target="_blank">{college.get('basic_info', {}).get('website', 'N/A')}</a></span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">📚 Programs</div>
"""
        
        programs = college.get('programs', {})
        if programs and not programs.get('error'):
            ug_programs = programs.get('ug_programs', [])
            pg_programs = programs.get('pg_programs', [])
            phd_programs = programs.get('phd_programs', [])
            
            if ug_programs:
                html_content += "<div class='data-field'><span class='field-label'>UG Programs:</span><ul class='programs-list'>"
                for prog in ug_programs[:5]:  # Show first 5
                    html_content += f"<li>{prog}</li>"
                html_content += "</ul></div>"
            
            if pg_programs:
                html_content += "<div class='data-field'><span class='field-label'>PG Programs:</span><ul class='programs-list'>"
                for prog in pg_programs[:5]:  # Show first 5
                    html_content += f"<li>{prog}</li>"
                html_content += "</ul></div>"
        else:
            html_content += "<div class='error'>No program data available</div>"
        
        html_content += """
        </div>
        
        <div class="section">
            <div class="section-title">💼 Placements</div>
"""
        
        placements = college.get('placements', {})
        if placements and not placements.get('error'):
            highest_pkg = placements.get('placements', {}).get('highest_package', 'N/A')
            avg_pkg = placements.get('placements', {}).get('average_package', 'N/A')
            placement_rate = placements.get('placements', {}).get('placement_rate_percent', 'N/A')
            
            html_content += f"""
            <div class="data-field">
                <span class="field-label">Highest Package:</span> 
                <span class="field-value">{highest_pkg} LPA</span>
            </div>
            <div class="data-field">
                <span class="field-label">Average Package:</span> 
                <span class="field-value">{avg_pkg} LPA</span>
            </div>
            <div class="data-field">
                <span class="field-label">Placement Rate:</span> 
                <span class="field-value">{placement_rate}%</span>
            </div>
"""
        else:
            html_content += "<div class='error'>No placement data available</div>"
        
        html_content += """
        </div>
        
        <div class="section">
            <div class="section-title">💰 Fees</div>
"""
        
        fees = college.get('fees', {})
        if fees and not fees.get('error'):
            ug_fees = fees.get('fees', {}).get('UG', {}).get('per_year', 'N/A')
            pg_fees = fees.get('fees', {}).get('PG', {}).get('per_year', 'N/A')
            
            html_content += f"""
            <div class="data-field">
                <span class="field-label">UG Fees (per year):</span> 
                <span class="field-value">₹{ug_fees}</span>
            </div>
            <div class="data-field">
                <span class="field-label">PG Fees (per year):</span> 
                <span class="field-value">₹{pg_fees}</span>
            </div>
"""
        else:
            html_content += "<div class='error'>No fee data available</div>"
        
        html_content += """
        </div>
        
        <div class="section">
            <div class="section-title">🏗️ Infrastructure</div>
"""
        
        infrastructure = college.get('infrastructure', {})
        if infrastructure and not infrastructure.get('error'):
            facilities = infrastructure.get('infrastructure', [])
            if facilities:
                html_content += "<div class='data-field'><span class='field-label'>Facilities:</span><ul class='programs-list'>"
                for facility in facilities[:5]:  # Show first 5
                    html_content += f"<li><strong>{facility.get('facility', 'N/A')}:</strong> {facility.get('details', '')}</li>"
                html_content += "</ul></div>"
        else:
            html_content += "<div class='error'>No infrastructure data available</div>"
        
        html_content += """
        </div>
    </div>
"""
    
    html_content += """
</body>
</html>
"""
    
    # Save HTML file
    with open('/home/ramji/Videos/scap/index.html', 'w') as f:
        f.write(html_content)
    
    print(f"✓ HTML created: /home/ramji/Videos/scap/index.html")
    print(f"✓ Total colleges displayed: {len(colleges_data)}")

if __name__ == "__main__":
    fetch_from_redis_and_create_html()

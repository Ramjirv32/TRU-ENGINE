import subprocess, json, time, re

API_KEY = "c138d04299d00500bdf9168ba3a04143fadcae1fab8437f2c4bb9b5437dc24d8"
q = 'For the college named RVS College of Engineering and Technology, located in India (Tamil Nadu), find the latest verified placement data for 2023 or 2024. Return only valid JSON with: guessed_data, data_year, sources, placements, placement_comparison_last_3_years, top_recruiters, placement_highlights. Do not add any extra text, only JSON.'

cmd = ["curl", "--get", "https://serpapi.com/search", "--data-urlencode", "engine=google_ai_mode", "--data-urlencode", f"q={q}", "--data-urlencode", f"api_key={API_KEY}"]
result = subprocess.run(cmd, capture_output=True, text=True)
data = json.loads(result.stdout)
markdown = data.get("reconstructed_markdown", "")

match = re.search(r"```json\s*(.*?)\s*```", markdown, re.DOTALL)
if match:
    parsed = json.loads(match.group(1))
    print(json.dumps(parsed, indent=2))
else:
    print("No json block found")
    print("Raw:", markdown[:1000])

import json
import re

with open("/home/ramji/Videos/scap/college_scraper/serper_results.json", "r") as f:
    data = json.load(f)

for college_name, college_data in data["colleges"].items():
    for query_type, query_data in college_data["queries"].items():
        markdown = query_data.get("reconstructed_markdown", "")
        
        match = re.search(r"```json\s*(.*?)\s*```", markdown, re.DOTALL)
        if match:
            json_str = match.group(1)
            try:
                parsed = json.loads(json_str)
                query_data["parsed_json"] = parsed
            except json.JSONDecodeError as e:
                query_data["parsed_json"] = None
                query_data["parse_error"] = str(e)
        else:
            query_data["parsed_json"] = None
            query_data["parse_error"] = "No ```json block found"

output_file = "/home/ramji/Videos/scap/college_scraper/serper_results_parsed.json"
with open(output_file, "w") as f:
    json.dump(data, f, indent=2)

print(f"Saved to: {output_file}")
print("\nSample - NIT Trichy infrastructure parsed_json:")
print(json.dumps(data["colleges"]["National Institute of Technology Tiruchirappalli"]["queries"]["infrastructure"]["parsed_json"], indent=2)[:500])

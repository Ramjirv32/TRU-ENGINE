import json
import redis

def store_serper_results_in_redis():
    # Load serper results
    with open('/home/ramji/Videos/scap/college_scraper/serper_results.json', 'r') as f:
        data = json.load(f)
    
    # Connect to Redis
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # Store each college with key format: college_name_country
    for college_name, college_data in data.get('colleges', {}).items():
        # Create structured data
        structured_data = {
            'college_name': college_name,
            'basic_info': college_data.get('basic_info', {}),
            'programs': college_data.get('programs', {}),
            'placements': college_data.get('placements', {}),
            'fees': college_data.get('fees', {}),
            'infrastructure': college_data.get('infrastructure', {}),
            'metadata': college_data.get('_metadata', {})
        }
        
        # Extract country from basic_info or use default
        country = structured_data['basic_info'].get('country', 'Unknown')
        
        # Create Redis key
        redis_key = f"{college_name.lower().replace(' ', '_')}_{country.lower()}"
        
        # Store in Redis
        r.set(redis_key, json.dumps(structured_data))
        print(f"✓ Stored in Redis: {redis_key}")
    
    print(f"\nTotal colleges stored in Redis: {len(data.get('colleges', {}))}")

if __name__ == "__main__":
    store_serper_results_in_redis()

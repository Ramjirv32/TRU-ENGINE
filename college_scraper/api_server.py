from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import json
import os
import redis

app = Flask(__name__)
CORS(app)


try:
    r = redis.Redis(host='localhost', port=6379, db=0)
    r.ping()  
    redis_available = True
except:
    redis_available = False
    print("Redis not available, using JSON file fallback")


@app.route('/')
def serve_index():
    """Serve the main HTML dashboard"""
    return send_from_directory('..', 'index.html')



@app.route('/api/college/<college_name>', methods=['GET'])
@app.route('/api/college', methods=['POST'])
def get_college_data(college_name=None):
    """Get college data from Redis or JSON fallback"""
    

    if college_name is None:
        try:
            request_data = request.get_json()
            college_name = request_data.get('college_name') if request_data else None
        except:
            return jsonify({"error": "Invalid request"}), 400
    
    if not college_name:
        return jsonify({"error": "College name required"}), 400
 
    if redis_available:
        try:
            key = f"{college_name.lower().replace(' ', '_')}_indonesia"
            data = r.get(key)
            if data:
                return jsonify(json.loads(data))
        except Exception as e:
            print(f"Redis error: {e}")
   
    try:
        with open('serper_results.json', 'r') as f:
            results = json.load(f)
            colleges = results.get('colleges', {})
            
          
            for name, data in colleges.items():
                if name.lower() == college_name.lower():
                    return jsonify(data)
            
            return jsonify({"error": "College not found"}), 404
    except Exception as e:
        return jsonify({"error": f"Data file error: {str(e)}"}), 500

@app.route('/api/colleges')
def list_colleges():
    """List all available colleges"""
    try:
        with open('serper_results.json', 'r') as f:
            results = json.load(f)
            colleges = list(results.get('colleges', {}).keys())
            return jsonify({"colleges": colleges})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting College Dashboard API Server...")
    print("Dashboard will be available at: http://localhost:5000")
    print("API endpoints:")
    print("  GET /api/colleges - List all colleges")
    print("  GET /api/college/<name> - Get specific college data")
    
    app.run(host='0.0.0.0', port=5000, debug=True)

from flask import Flask, request, jsonify
from datetime import datetime
import json
import os
import threading
import time

app = Flask(__name__)

# Store clients in memory (will reset if Render restarts)
clients = {}
data_log = []

# File to persist data (Render has persistent disk if enabled)
DATA_FILE = 'collected_data.json'

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': 'active',
        'message': 'Data collection server running',
        'endpoints': {
            '/api/log': 'POST - Send client data',
            '/api/clients': 'GET - View all clients',
            '/api/stats': 'GET - View statistics'
        }
    })

@app.route('/api/log', methods=['POST'])
def receive_data():
    try:
        # Get JSON data from request
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No JSON data received'}), 400
        
        # Add server timestamp
        data['server_received_at'] = datetime.now().isoformat()
        
        # Store in memory
        computer_name = data.get('ComputerName', 'Unknown_' + str(len(clients)))
        clients[computer_name] = {
            'data': data,
            'last_seen': datetime.now().isoformat()
        }
        
        # Store in log list
        data_log.append(data)
        
        # Append to file for persistence
        try:
            with open(DATA_FILE, 'a') as f:
                f.write(json.dumps(data) + '\n')
        except:
            pass  # Write to file if possible
        
        # Print to console (Render logs will show this)
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Received from: {computer_name}")
        print(f"  IP: {data.get('IPAddress', 'Unknown')}")
        print(f"  User: {data.get('Username', 'Unknown')}")
        print(f"  Time: {data.get('Timestamp', 'Unknown')}")
        
        return jsonify({
            'status': 'success',
            'message': 'Data received',
            'computer': computer_name
        }), 200
        
    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/clients', methods=['GET'])
def get_clients():
    """Return all stored clients"""
    client_list = []
    for name, info in clients.items():
        client_data = info['data'].copy()
        client_data['last_seen'] = info['last_seen']
        client_list.append(client_data)
    
    return jsonify({
        'total': len(client_list),
        'clients': client_list
    })

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Return statistics"""
    return jsonify({
        'total_clients': len(clients),
        'total_entries': len(data_log),
        'active_today': sum(1 for c in clients.values() 
                          if datetime.fromisoformat(c['last_seen']).date() == datetime.now().date()),
        'server_time': datetime.now().isoformat()
    })

@app.route('/api/clear', methods=['POST'])
def clear_data():
    """Clear all stored data (admin use)"""
    global clients, data_log
    clients.clear()
    data_log.clear()
    return jsonify({'status': 'success', 'message': 'All data cleared'})

# Health check endpoint for Render
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Server starting on port {port}")
    print(f"Data file: {DATA_FILE}")
    app.run(host='0.0.0.0', port=port)

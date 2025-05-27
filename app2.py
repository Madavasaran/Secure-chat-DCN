from flask import Flask, render_template, request, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
import os
import time
import random
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
app.config['UPLOAD_FOLDER'] = 'uploads'
socketio = SocketIO(app, ping_timeout=5, ping_interval=5)


# Add at the top of your Flask file
active_connections = 0

@socketio.on('connect')
def handle_connect():
    global active_connections
    active_connections += 1
    emit('update_connections', {'count': active_connections}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    global active_connections
    active_connections -= 1
    emit('update_connections', {'count': active_connections}, broadcast=True)

# Enhanced Caesar Cipher with configurable shift
def caesar_cipher(text, shift=3, encrypt=True):
    if not encrypt:
        shift = -shift
    result = ""
    for char in text:
        if char.isalpha():
            shift_base = 65 if char.isupper() else 97
            result += chr((ord(char) - shift_base + shift) % 26 + shift_base)
        else:
            result += char
    return result

@app.route('/')
def index():
    return render_template('index2.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/upload', methods=['POST'])
def upload():
    start_time = time.time()
    file = request.files['file']
    
    if file.filename == '':
        return ('No file selected', 400)

    # Simulate 10% packet drop
    if random.random() < 0.1:
        socketio.emit('file_status', {
            'status': 'Packet dropped during file upload',
            'timestamp': datetime.now().strftime('%H:%M:%S')
        })
        return ('Packet dropped simulation', 202)

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    transfer_time = time.time() - start_time
    file_size_kb = os.path.getsize(filepath) / 1024
    throughput = file_size_kb / transfer_time if transfer_time > 0 else 0

    socketio.emit('file_uploaded', {
        'filename': filename,
        'size_kb': f"{file_size_kb:.2f}",
        'latency_ms': f"{transfer_time * 1000:.2f}",
        'throughput': f"{throughput:.2f}",
        'url': f"/uploads/{filename}",
        'timestamp': datetime.now().strftime('%H:%M:%S')
    })

    return ('', 204)

@socketio.on('send_message')
def handle_message(data):
    # Get the client's timestamp if available
    client_timestamp = data.get('timestamp', time.time() * 1000)
    timestamp = datetime.now().strftime('%H:%M:%S')
    
    # Simulate 10% packet drop
    if random.random() < 0.1:
        emit('receive_message', {
            'original': data['message'],
            'encrypted': '--- Packet Dropped ---',
            'decrypted': '--- N/A ---',
            'latency_ms': 'N/A',
            'timestamp': timestamp,
            'client_timestamp': client_timestamp
        }, broadcast=True)
        return

    encrypted = caesar_cipher(data['message'])
    decrypted = caesar_cipher(encrypted, encrypt=False)
    
    # Calculate server processing time
    server_processing_time = (time.time() * 1000) - client_timestamp
    
    emit('receive_message', {
        'original': data['message'],
        'encrypted': encrypted,
        'decrypted': decrypted,
        'latency_ms': f"{server_processing_time:.2f}",
        'timestamp': timestamp,
        'client_timestamp': client_timestamp
    }, broadcast=True)

@socketio.on('ping_from_client')
def handle_ping(data):
    emit('pong_from_server', {
        'timestamp': data['timestamp'],
        'server_time': datetime.now().strftime('%H:%M:%S')
    })

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
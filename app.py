from flask import Flask, render_template, request, redirect, url_for, flash
import subprocess
import json
import re
import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables from .env

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Needed for flashing messages

def list_interfaces():
    interfaces = []
    result = subprocess.run(['ip', '-j', 'addr'], capture_output=True, text=True)
    output = result.stdout
    data = json.loads(output)

    for interface in data:
        interface_name = interface['ifname']
        ip_address = None
        for addr_info in interface.get('addr_info', []):
            if addr_info['family'] == 'inet':
                ip_address = addr_info['local']
                break
        if ip_address:
            latency = get_latency(interface_name)
            loss = get_loss(interface_name)
            bandwidth = get_bandwidth(interface_name)
            interfaces.append({'name': interface_name, 'ip': ip_address, 'latency': latency, 'loss': loss, 'bandwidth': bandwidth})

    return interfaces

def get_latency(interface):
    result = subprocess.run(['tc', 'qdisc', 'show', 'dev', interface], capture_output=True, text=True)
    output = result.stdout
    match = re.search(r'delay (\d+ms)', output)
    return match.group(1) if match else '0ms'

def get_loss(interface):
    result = subprocess.run(['tc', 'qdisc', 'show', 'dev', interface], capture_output=True, text=True)
    output = result.stdout
    match = re.search(r'loss (\d+)%', output)
    return match.group(1) + '%' if match else '0%'

def get_bandwidth(interface):
    result = subprocess.run(['tc', 'class', 'show', 'dev', interface], capture_output=True, text=True)
    output = result.stdout
    match = re.search(r'rate (\d+Kbit)', output)
    return match.group(1) if match else 'N/A'

def apply_latency(interface, latency):
    result = subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'netem', 'delay', latency], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Error applying latency: {result.stderr}")

def apply_loss(interface, loss):
    result = subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'netem', 'loss', loss], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Error applying loss: {result.stderr}")

def apply_bandwidth(interface, bandwidth):
    result = subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'handle', '1:', 'htb'], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Error setting up root qdisc: {result.stderr}")
    result = subprocess.run(['sudo', 'tc', 'class', 'add', 'dev', interface, 'parent', '1:', 'classid', '1:1', 'htb', 'rate', bandwidth], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Error applying bandwidth: {result.stderr}")

def remove_degradations(interface):
    result = subprocess.run(['sudo', 'tc', 'qdisc', 'del', 'dev', interface, 'root'], capture_output=True, text=True)
    if result.returncode != 0:
        flash(f"Error removing degradations: {result.stderr}")

@app.route('/')
def index():
    interfaces = list_interfaces()
    return render_template('index.html', interfaces=interfaces)

@app.route('/apply', methods=['POST'], endpoint='apply_interface')
def apply():
    interface = request.form['interface'].split(' ')[0]  # Extract the interface name
    latency = request.form.get('latency')
    loss = request.form.get('loss')
    bandwidth = request.form.get('bandwidth')
    
    if latency:
        apply_latency(interface, latency)
    if loss:
        apply_loss(interface, loss)
    if bandwidth:
        apply_bandwidth(interface, bandwidth)
    
    return redirect(url_for('index'))

@app.route('/remove', methods=['POST'], endpoint='remove_interface')
def remove():
    interface = request.form['interface'].split(' ')[0]  # Extract the interface name
    remove_degradations(interface)
    return redirect(url_for('index'))

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    app.run(host=host, port=port, debug=True)
from flask import Flask, render_template, request, redirect, url_for
import subprocess
import json
import re

app = Flask(__name__)

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
            interfaces.append({'name': interface_name, 'ip': ip_address, 'latency': latency, 'loss': loss})

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

def apply_latency(interface, latency):
    subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'netem', 'delay', latency])

def apply_loss(interface, loss):
    subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', interface, 'root', 'netem', 'loss', loss])

def remove_degradations(interface):
    subprocess.run(['sudo', 'tc', 'qdisc', 'del', 'dev', interface, 'root'])

@app.route('/')
def index():
    interfaces = list_interfaces()
    return render_template('index.html', interfaces=interfaces)

@app.route('/apply', methods=['POST'])
def apply():
    interface = request.form['interface'].split(' ')[0]  # Extract the interface name
    latency = request.form.get('latency')
    loss = request.form.get('loss')
    
    if latency:
        apply_latency(interface, latency)
    if loss:
        apply_loss(interface, loss)
    
    return redirect(url_for('index'))

@app.route('/remove', methods=['POST'])
def remove():
    interface = request.form['interface'].split(' ')[0]  # Extract the interface name
    remove_degradations(interface)
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
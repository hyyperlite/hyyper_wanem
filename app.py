from flask import Flask, render_template, request, redirect, url_for
import subprocess

app = Flask(__name__)

def list_interfaces():
    result = subprocess.run(['ls', '/sys/class/net'], stdout=subprocess.PIPE)
    interfaces = result.stdout.decode('utf-8').split()
    interfaces_with_details = []
    for interface in interfaces:
        ip_result = subprocess.run(['ip', 'addr', 'show', interface], stdout=subprocess.PIPE)
        ip_output = ip_result.stdout.decode('utf-8')
        ip_address = "No IP"
        for line in ip_output.split('\n'):
            if 'inet ' in line:
                ip_address = line.strip().split()[1].split('/')[0]
                break
        
        # Get current degradations
        tc_result = subprocess.run(['tc', 'qdisc', 'show', 'dev', interface], stdout=subprocess.PIPE)
        tc_output = tc_result.stdout.decode('utf-8')
        latency = "None"
        loss = "None"
        for line in tc_output.split('\n'):
            if 'delay' in line:
                latency = line.strip().split('delay ')[1].split(' ')[0]
            if 'loss' in line:
                loss = line.strip().split('loss ')[1].split(' ')[0]
        
        interfaces_with_details.append({
            'name': interface,
            'ip': ip_address,
            'latency': latency,
            'loss': loss
        })
    return interfaces_with_details

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
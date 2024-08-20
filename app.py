from flask import Flask, render_template, request, redirect, url_for
import subprocess

app = Flask(__name__)

def list_interfaces():
    # Dummy data for example purposes
    return [
        {'name': 'eth0', 'ip': '192.168.1.1', 'latency': '10ms', 'loss': '0%'},
        {'name': 'wlan0', 'ip': '192.168.1.2', 'latency': '20ms', 'loss': '1%'}
    ]

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
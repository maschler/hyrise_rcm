#!/bin/bash
echo "127.0.0.1 $(hostname)" | sudo tee -a /etc/hosts

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git python3-pip python3-dev npm

git clone https://github.com/maschler/hyrise_rcm.git
cd hyrise_rcm/
sudo pip3 install -r requirements.txt 
 
cd static
#curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
#sudo apt-get install -y nodejs
npm install
npm run tsc

# Install python3.5 and link python3.4 packages
sudo add-apt-repository ppa:fkrull/deadsnakes -y
sudo apt-get update
sudo apt-get install -y python3.5

sudo rm -r /usr/local/lib/python3.5/dist-packages/
sudo ln -s /usr/local/lib/python3.4/dist-packages /usr/local/lib/python3.5/dist-packages

# Setup iptables rules for forwarding
sudo iptables -A FORWARD -i lo -o eth1 -p tcp --syn --dport 5000 -m conntrack --ctstate NEW -j ACCEPT
sudo iptables -A FORWARD -i lo -o eth1 -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -A FORWARD -i eth1 -o lo -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
sudo iptables -P FORWARD DROP

#sudo iptables -t nat -A PREROUTING -i eth0 -p tcp --dport 5000 -j DNAT --to-destination 127.0.0.1
#sudo iptables -t nat -A POSTROUTING -o eth1 -p tcp --dport 5000 -d 127.0.0.1 -j SNAT --to-source 192.168.124.101
sudo iptables-save | sudo tee /etc/iptables/rules.v4

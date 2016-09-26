#!/bin/bash
set -ex

curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python-pip python-dev nodejs

cd ~/hyrise_rcm/
sudo pip install -r requirements.txt 
sudo cp hyrise_rcm.conf /etc/init/
 
cd static
rm -r node_modules
npm install | xargs echo
npm run tsc

sudo service hyrise_rcm start


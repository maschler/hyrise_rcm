#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y python-pip python-dev npm

cp -r /vagrant/ ~/hyrise_rcm
cd hyrise_rcm/
sudo pip install -r requirements.txt 
sudo cp hyrise_rcm.conf /etc/init/
 
cd static
curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install | xargs echo
npm run tsc || true

sudo service hyrise_rcm start


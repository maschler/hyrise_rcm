#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git python3-pip python3-dev npm

cp -r /vagrant/ ~/hyrise_rcm
cd hyrise_rcm/
sudo pip3 install -r requirements.txt 
sudo cp hyrise_rcm.conf /etc/init/
 
cd static
curl -sL https://deb.nodesource.com/setup_4.x | sudo -E bash -
sudo apt-get install -y nodejs
npm install | xargs echo
npm run tsc || true

# Install python3.5 and link python3.4 packages
sudo add-apt-repository ppa:fkrull/deadsnakes -y
sudo apt-get update
sudo apt-get install -y python3.5

sudo rm -r /usr/local/lib/python3.5/dist-packages/
sudo ln -s /usr/local/lib/python3.4/dist-packages /usr/local/lib/python3.5/dist-packages

sudo service hyrise_rcm start


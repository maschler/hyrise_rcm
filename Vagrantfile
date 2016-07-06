Vagrant.configure(2) do |config|
  config.vm.box = "ubuntu/trusty64"
  config.vm.provision :shell, path: "provision.sh", privileged: false
  config.vm.network :private_network, :ip => "192.168.123.101", :libvirt__forward_mode => 'none'
  config.vm.network "forwarded_port", guest: 5000, host: 8080
  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"
#  config.vm.provision :shell, path: "run.sh", run: "always", privileged: true
end

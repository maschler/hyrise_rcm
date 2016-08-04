Vagrant.configure(2) do |config|
  config.vm.box = "cloud-trusty64"
  config.vm.provision :shell, path: "provision.sh", privileged: false
  config.vm.network :private_network, :ip => "192.168.123.101", :libvirt__forward_mode => 'none'
  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"
  config.ssh.insert_key = false
end

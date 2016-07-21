Vagrant.configure(2) do |config|
  config.vm.box = "cloud-trusty64"
  config.vm.provider :libvirt do |provider|
    provider.cpus = 2
    provider.memory = 2048
  end
  config.vm.provision :shell, path: "provision.sh", privileged: false
  config.vm.network :private_network, :ip => "192.168.123.101", :libvirt__forward_mode => 'none'
  config.vm.network "forwarded_port", guest: 5000, host: 8080
  config.ssh.shell = "bash -c 'BASH_ENV=/etc/profile exec bash'"
  config.ssh.insert_key = false
#  config.vm.provision :shell, path: "run.sh", run: "always", privileged: true
end

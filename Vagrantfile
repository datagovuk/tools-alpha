# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|

  # Allow local machines to view the VM
  config.vm.network "private_network", ip: "192.168.1.15"

  config.vm.provider :virtualbox do |vb|
    config.vm.box = "ubuntu/trusty64"
    vb.gui = false

    vb.customize ["modifyvm", :id, "--name", "tool_alpha_dev"]
    vb.customize ["modifyvm", :id, "--memory", "2048"]
    vb.customize ["modifyvm", :id, "--cpus", "2"]
    vb.customize ["modifyvm", :id, "--ioapic", "on"]
  end


end

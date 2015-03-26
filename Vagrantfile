# -*- mode: ruby -*-
# vi: set ft=ruby :

# Vagrantfile API/syntax version. Don't touch unless you know what you're doing!
VAGRANTFILE_API_VERSION = "2"

COREOS_UPDATE_CHANNEL = "stable"
COREOS_CLOUD_CONFIG_PATH = File.join(File.dirname(__FILE__), "cloud-config.yml")

Vagrant.configure(VAGRANTFILE_API_VERSION) do |config|
  config.vm.box = "coreos-#{COREOS_UPDATE_CHANNEL}"
  config.vm.box_version = ">= 308.0.1"
  config.vm.box_url = "http://#{COREOS_UPDATE_CHANNEL}.release.core-os.net/amd64-usr/current/coreos_production_vagrant.json"

  config.vm.network "forwarded_port", :guest => 8080, :host => 8080

  config.vm.provider :virtualbox do |v|
    # On VirtualBox, we don't have guest additions or a functional vboxsf
    # in CoreOS, so tell Vagrant that so it can be smarter.
    v.check_guest_additions = false
    v.functional_vboxsf     = false
  end

  config.vm.provider :virtualbox do |v|
    v.memory = 512
    v.cpus   = 1
  end

  if File.exist?(COREOS_CLOUD_CONFIG_PATH)
    config.vm.provision :file, :source => "#{COREOS_CLOUD_CONFIG_PATH}", :destination => "/tmp/vagrantfile-user-data"
    config.vm.provision :shell, :inline => "mv /tmp/vagrantfile-user-data /var/lib/coreos-vagrant/"
  end

end

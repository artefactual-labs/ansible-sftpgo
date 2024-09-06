# Table of Contents

- [Scenario Description](#scenario-description)
  - [The Permissions Issue](#the-permissions-issue)
  - [Using bindfs to Solve Permissions Issues](#using-bindfs-to-solve-permissions-issues)
  - [Directory Structure and Users](#directory-structure-and-users)
  - [bindfs Mount Configuration](#bindfs-mount-configuration)
  - [sftpgo Users and SSH Configuration](#sftpgo-users-and-ssh-configuration)
  - [SFTPGo and Web Client Configuration](#sftpgo-and-web-client-configuration)
  - [Firewall Configuration](#firewall-configuration)
- [Preparing Ansible config files and playbook](#preparing-ansible-config-files-and-playbook)
  - [New sftpgo group](#new-sftpgo-group)
  - [Changes in ansible inventory file](#changes-in-ansible-inventory-file)
  - [Add ansible-sftpgo role to requirements file](#add-ansible-sftpgo-role-to-requirements-file)
  - [Add sftpgo.yml file to host_vars dir](#add-sftpgoyml-file-to-host_vars-dir)
  - [Add sftpgo.yml playbook](#add-sftpgoyml-playbook)
- [Running playbook](#running-playbook)
- [Checking playbook results in VM](#checking-playbook-results-in-vm)
  
  
---

# Scenario Description

In this example, we already have AtoM deployed in a single VM, along with an existing Ansible environment. AtoM (Access to Memory) is an open-source archival description software that allows institutions to manage and provide access to their digital collections. We aim to extend this existing AtoM deployment by adding `sftpgo` to simplify file uploads (both static content and digital objects) for AtoM via SFTP.

We want to use `sftpgo` to:

* Upload static content for AtoM in a directory. See: [Add static images to static-pages in AtoM](https://www.accesstomemory.org/en/docs/2.7/user-manual/administer/static-pages/#static-image)
* Upload CSV files and digital objects to the VM for use with AtoM commands run from the CLI.

### The Permissions Issue

A potential permissions issue arises because files uploaded via `sftpgo` are owned by the `sftpgo` user, while AtoM processes—running under the `www-data` or `nginx` user—require access to these files. Without resolving this issue, AtoM cannot read or modify the files as needed. To address this, we use [bindfs](https://bindfs.org/), which allows us to mount directories with different ownership and permissions, without modifying the underlying file ownership on the disk.

`bindfs` is a FUSE filesystem that allows us to mount a directory and change its permissions or ownership in the mounted view. This is a useful solution because it ensures that AtoM can access files uploaded via SFTP without changing the original ownership or permissions of the files managed by `sftpgo`. By mounting directories with `bindfs`, we can ensure that AtoM's `www-data` user has the necessary read and write permissions on the mounted directories while maintaining `sftpgo` user ownership.

### Directory Structure and Users

We are going to add two users to `sftpgo`, sharing the same `sftpgo` home directory: `/home/sftpgo`.

Inside the home directory, we will create two subdirectories (which cannot be deleted by `sftpgo` users):

* **Static**: `/home/sftpgo/static`
* **AtoM Uploads**: `/home/sftpgo/atom_uploads`

To maintain security and integrity, it’s important that the `sftpgo` users (e.g., `customer` and `artefactual`) can upload files to the `atom_uploads` and `static` directories but cannot delete the directories themselves. This ensures that key directories remain intact while providing flexibility for file management. The `static` directory only requires read access, while the `atom_uploads` directory requires both read and write access to allow file manipulation via the AtoM CLI.

### bindfs Mount Configuration

We will configure two `bindfs` mounts:

* `/home/atomadm/static`: Points to the static `sftpgo` directory with `www-data` as the owner and `0550` permissions (read-only for `www-data`).
* `/mnt/atom_uploads`: Points to the `atom_uploads` directory with `www-data` as the owner and `0750` permissions (read/write for `www-data`).

We need the static content to be in `/home/atomadm/static` because we already have this configuration in the AtoM Nginx site:

```
  location /static/ {
    alias /home/atomadm/static/;
    autoindex off;
    }
```


### sftpgo Users and SSH Configuration

We will add two `sftpgo` users, each with specific SSH authentication methods and network access restrictions:

- **`customer`**:
  - **Authentication**: This user will authenticate using two public SSH keys provided by the customer.
  - **Network Access**: The `customer` user will be allowed access from the `5.5.5.0/24` network.

- **`artefactual`**:
  - **Authentication**: This user will authenticate using a set of pre-existing public SSH keys, stored as separate files in an Ansible-managed directory.
  - **Network Access**: The `artefactual` user will be allowed access from the `6.6.6.0/24` network.

These network restrictions ensure that each user can only access the SFTP service from their respective networks, enhancing security by limiting access based on IP address.


### SFTPGo and Web Client Configuration

The `sftpgo` service will listen on port `22222` for SFTP connections, and the `sftpgo` web client will run on port `7777`, proxied through Nginx. The web client will be accessible via a reverse proxy configured using the existing [Ansible nginx role](https://github.com/artefactual-labs/ansible-nginx). Nginx will proxy incoming requests on port `7777` to the `sftpgo` web client (listening on `http://localhost:8081`). This configuration ensures that the web client is accessible externally while maintaining separation between AtoM and `sftpgo` services.

### Firewall Configuration

We will configure UFW firewall rules to allow access to the following:

* **SFTP (port 22222)**: Access allowed from from both the `5.5.5.0/24` and `6.6.6.0/24` networks.
* **SFTPGo web client (port 7777)**: Access allowed from both the `5.5.5.0/24` and `6.6.6.0/24` networks.


# Preparing Ansible config files and playbook

This assumes an existing Ansible environment for AtoM deployment. We will:

* Create a new sftpgo group with common configuration for SFTPGo, firewall, and Nginx across AtoM VMs.
* Modify the Ansible inventory to include AtoM VM in the sftpgo group.
* Add the role to the `requirements.yml` file.
* Add host-specific variables for the new playbook in the `host_vars` directory.
* Create a new playbook to deploy SFTPGo and configure bindfs, including firewall and Nginx configuration.



### New sftpgo group

Though optional, creating an sftpgo group simplifies configuration in the host_vars files by centralizing common settings.

This file is have several sections that will be explained in next subsections. [Here](atom-example/sftpgo) you can find the complete file.

Create the group by adding the `group_vars/sftpgo` file with the following content:

1. SFTPGo role variables 

```yaml
sftpgo_path_ssh_keys: "files/ssh_keys/"

sftpgo_no_log: True

sftpgo_api_auth_user: artef_admin_api_user
sftpgo_api_auth_key: "SUPERSECRETKEY" # Must be in vault format
          

sftpgo_httpd_bind_port: 8081
sftpgo_httpd_bind_address: 127.0.0.1

sftpgo_sftpd_bind_port: 22222
sftpgo_sftpd_bind_address: ""  # Listen in all VM addresses when empty

sftpgo_bindfs_mounts:
  - src: /home/sftpgo/atom_uploads
    path: /mnt/atom_uploads
    user: "{{ nginx_user }}"
    group: "{{ nginx_user }}"
    perms: 750
  - src: /home/sftpgo/static
    path: /home/atomadm/static
    user: "{{ nginx_user }}"
    group: "{{ nginx_user }}"
    perms: 550

sftpgo_users: []
```

The environment was already using some ssh pub key files in the `files/ssh_keys` dir:

```bash
cascadito ~/artefactual/atom-test-deployment/files $ tree
.
└── ssh_keys
    ├── user1.pub
    ├── user2.pub
    ├── user3.pub
    ├── user4.pub
    ├── user5.pub
    ├── user6.pub
    └── user7.pub
```

The `nginx_user` will be defined in this file in nginx section

`sftpgo_users` is an empty dict because we are going to define in every host_vars file, becuse it will be different for every customer


2. Nginx role variables

```yaml
nginx_user: "{% if ansible_os_family in ['RedHat','Rocky'] %}nginx{% elif ansible_os_family == 'Debian' %}www-data{% endif %}"

nginx_sftpgo_sites:
  sftpgo:
    - listen 7777 ssl
    - server_name {{ server_name|default('_') }} {{ server_alias | default('') }}
    - ssl_certificate {{ sftpgo_https_certificate | default('/var/lib/acme/live/'+server_name+'/fullchain') }}
    - ssl_certificate_key {{ sftpgo_https_certificate_key | default('/var/lib/acme/live/'+server_name+'/privkey') }}
    - ssl_session_timeout 5m
    - ssl_session_cache shared:SSL:50m
    - ssl_protocols TLSv1.2 TLSv1.3
    - ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305'
    - ssl_prefer_server_ciphers on
    - add_header Strict-Transport-Security max-age=63072000
    - client_max_body_size {{ sftpgo_nginx_post_max_size | default('520M') }}
    - proxy_max_temp_file_size {{ sftpgo_nginx_proxy_max_temp_file_size | default('1024m') }}
    - location / {
        proxy_pass http://{{ sftpgo_httpd_bind_address | default('127.0.0.1') }}:{{ sftpgo_httpd_bind_port | default('8081') }};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
      }
    - location /api/ {
        deny all;
      }

```

Here we are defining the `nginx_user` based in Linux Distribution and the `nginx_sftpgo_sites` is a site config to be used with the [ansible-nginx role](https://github.com/artefactual-labs/ansible-nginx)

3. Firewall settings

```yaml
sftpgo_allowed_src_networks:
  - "6.6.6.0/24" # Artefactual network
```
Here we are defining the `sftpgo_allowed_src_networks` with the allowed networks. You can override `sftpgo_allowed_src_networks` in the `host_vars` file for each customer.

4. Artefactual ssh keys

```yaml
key_list:
  - 'user1.pub'
  - 'user2.pub'
  - 'user3.pub'

```

We are including in the `key_list` list the name of ssh key files we want to add from `sftpgo_path_ssh_keys` directory.

### Changes in ansible inventory file

If the `atom-test` host is already defined in your inventory, add the VM to the new sftpgo group by appending the following to your hosts file:

```yaml
[sftpgo]
atom-test
```

### Add ansible-sftpgo role to requirements file

In your requirements.yml, add the role with this configuration:

```yaml
- src: "https://github.com/artefactual-labs/ansible-sftpgo.git"
  name: "artefactual.sftpgo"
  version: "main"
```

### Add sftpgo.yml file to host_vars dir

Create a configuration file for the host at host_vars/atom-test/sftpgo.yml:

```yaml
---

# For nginx site
server_name: "example.accesstomemory.org"
server_alias: ""


# Define only when not using acmetool for certificates
#sftpgo_https_certificate: "/etc/ssl/private/XXXXXXX/YYYYYY.crt"
#sftpgo_https_certificate_key: "/etc/ssl/private/XXXXXXXX/ZZZZZZZZ.key"

sftpgo_users:
  - user: artefactual
    home_dir: /home/sftpgo
    home_dir_perms: '0550'
    create_subdirs:
      - static
      - atom_uploads
    subdir_perms: '0550'
    password: "THE_PASS" # Must be in vault format
    public_keys: [] # Empty list, we are only going to add keys from files
    public_keys_files: "{{ key_list }}"
  - user: customer
    home_dir: /home/sftpgo
    home_dir_perms: '0550'
    create_subdirs:
      - static
      - atom_uploads
    subdir_perms: '0550'
    password: "THE_PASS_2" # Must be in vault format
    public_keys:
      - "ssh-ed25519 AAAACFAKEHASHKEYAAAAAAAAAAAAAAAAAA user1@customer.com"
      - "ssh-ed25519 AAAACFAKEHASHKEYAAAAAAAAAAAAAAAAAA user1@customer.com"
    public_keys_files: [] # Empty list, we are not going to add keys from files
    


# Add customer public IP addresses/networks in the next list
sftpgo_allowed_src_networks:
  - "6.6.6.0/24" # artefactual
  - "5.5.5.0/24" # customer
```

This example defines nginx site variables, users, and allowed networks. Two users (artefactual and customer) share the same home directory structure, differing only in credentials. You can mix public_keys and public_keys_files for added flexibility.

### Add sftpgo.yml playbook

This playbook configures SFTPGo, Nginx, and the firewall. It includes SELinux adjustments to allow Nginx to use port 7777 if SELinux is enabled.

```yaml
- hosts: [sftpgo]

  pre_tasks:
  
    - name: "SELinux: Allow nginx to use port 7777"
      become: "yes"
      seport:
        ports: "7777"
        proto: "tcp"
        setype: "http_port_t"
        state: "present"
      when: ansible_selinux.status == "enabled"
      tags:
        - "selinux"

    - name: "Configure sftpgo (22222) access from allowed sources"
      become: "yes"
      ufw:
        rule: "allow"
        proto: "tcp"
        port: "22222"
        from_ip: "{{ item }}"
        state: "enabled"
      loop: "{{ sftpgo_allowed_src_networks }}"
      when: "sftpgo_allowed_src_networks is defined"
      tags:
        - "ufw"

    - name: "Configure sftpgo web client (7777) access from allowed sources"
      become: "yes"
      ufw:
        rule: "allow"
        proto: "tcp"
        port: "7777"
        from_ip: "{{ item }}"
        state: "enabled"
      loop: "{{ sftpgo_allowed_src_networks }}"
      when: "sftpgo_allowed_src_networks is defined"
      tags:
        - "ufw"
        
  roles:
  
    - role: "artefactual.sftpgo"
      become: yes
      tags:
        - "sftpgo"

    - role: "artefactual.nginx"
      become: "yes"
      nginx_configs: {}
      nginx_sites: "{{ nginx_sftpgo_sites }}"
      tags:
        - "nginx"
```

This playbook handles firewall configuration based on allowed networks, integrates Nginx and SFTPGo roles, and applies SELinux policies where needed.

[Here](atom-example/sftpgo.yml) you can download the playbook.

# Running playbook

To install or update the roles specified in requirements.yml, run the following command:

```bash
ansible-galaxy install -f -p roles/ -r requirements.yml
```

Run the playbook targeting the `atom-test` VM defined in your inventory:

```bash
ansible-playbook -i hosts -l atom-test sftpgo.yml
```

This command executes the sftpgo.yml playbook, applying the configuration to the atom-test host.

# Checking playbook results in VM

The AtoM VM should now be ready to use SFTPGo with SFTPD protocol (SSH keys only) and the SFTPGo web client.

In VM (Ubuntu 20) we can see:

1. Packages installed

Verify SFTPGo is installed from the Launchpad PPA:

```bash
artefactual@atom-test:~$ dpkg -l | grep sftpgo
ii  sftpgo                                2.6.2-1ppa1                                amd64        Full-featured and highly configurable SFTP server
```

We have installed sftpgo from http://ppa.launchpad.net/sftpgo/sftpgo/ubuntu repo.

2. SFTPGo config files

Ansible modifies:

* /etc/sftpgo/sftpgo.env
* /etc/sftpgo/sftpgo.json

All the other settings come from rpm or dpkg package.

3. Firewall rules

Check new UFW rules for ports 22222 and 7777:

```bash
artefactual@atom-test:~# sudo ufw status | grep -E '(7777|22222)'
22222/tcp                  ALLOW       5.5.5.0/24
22222/tcp                  ALLOW       6.6.6.0/24
7777/tcp                  ALLOW       5.5.5.0/24
7777/tcp                  ALLOW       6.6.6.0/24
```

4. nginx site

The following nginx site has been created:

* /etc/nginx/sites-enabled/sftpgo.conf

```bash
root@atom-test:~# ls -l /etc/nginx/sites-enabled/sftpgo.conf
lrwxrwxrwx 1 root root 38 Sep  4 09:09 /etc/nginx/sites-enabled/sftpgo.conf -> /etc/nginx/sites-available/sftpgo.conf
```

5. sftpgo home dir

Verify correct permissions (0550) for the SFTPGo home directory:

```bash
root@atom-test:~# stat /home/sftpgo
  File: /home/sftpgo
  Size: 4096      	Blocks: 8          IO Block: 4096   directory
Device: fc01h/64513d	Inode: 514025      Links: 4
Access: (0550/dr-xr-x---)  Uid: (  995/  sftpgo)   Gid: (  995/  sftpgo)
Access: 2024-09-04 11:40:12.853503022 +0000
Modify: 2024-09-04 11:32:45.927540561 +0000
Change: 2024-09-04 11:39:38.005038384 +0000
 Birth: -
```

It doesn't allow to create new files or dirs in the `/home/sftpgo` as sftpgo user.

The role created the following subdirs, each subdir with the permissions set in the `sftpgo_users` dict:

```bash
root@atom-test:~# ls -lh /home/sftpgo
total 8.0K
drwxr-x--- 2 sftpgo sftpgo 4.0K Sep  4 11:58 atom_uploads
drwxr-x--- 2 sftpgo sftpgo 4.0K Sep  4 18:58 static
```

When using sftpgo users, we can write/delete/update in both subdirectories. But `atom_uploads` and `static` dirs cannot be deleted (as we desired)

6. bindfs mount points

The role added to fstab and mounted:

```bash
/home/sftpgo/atom_uploads /mnt/atom_uploads fuse.bindfs force-user=www-data,force-group=www-data,create-for-user=www-data,create-for-group=www-data,create-with-perms=750,perms=750 0 0
/home/sftpgo/static /home/atomadm/static fuse.bindfs force-user=www-data,force-group=www-data,create-for-user=www-data,create-for-group=www-data,create-with-perms=550,perms=550 0 0
```

That is exactly what we defined in group:

```yaml
sftpgo_bindfs_mounts:
  - src: /home/sftpgo/atom_uploads
    path: /mnt/atom_uploads
    user: "{{ nginx_user }}"
    group: "{{ nginx_user }}"
    perms: 750
  - src: /home/sftpgo/static
    path: /home/atomadm/static
    user: "{{ nginx_user }}"
    group: "{{ nginx_user }}"
    perms: 550
```

We can see the bindfs mounts:

```yaml
root@atom-test:~# mount | grep sftpgo
/home/sftpgo/atom_uploads on /mnt/atom_uploads type fuse (rw,relatime,user_id=0,group_id=0,default_permissions,allow_other)
/home/sftpgo/static on /home/atomadm/static type fuse (rw,relatime,user_id=0,group_id=0,default_permissions,allow_other)
```

And we can check the permissions of bindfs mount points:

```yaml
root@atom-test:~# stat /mnt/atom_uploads
  File: /mnt/atom_uploads
  Size: 4096      	Blocks: 8          IO Block: 4096   directory
Device: 38h/56d	Inode: 513941      Links: 2
Access: (0750/drwxr-x---)  Uid: (   33/www-data)   Gid: (   33/www-data)
Access: 2024-09-05 17:22:23.169872158 +0000
Modify: 2024-09-04 11:58:24.324066213 +0000
Change: 2024-09-04 11:58:24.324066213 +0000
 Birth: -

root@atom-test:~# stat /home/atomadm/static
  File: /home/atomadm/static
  Size: 4096      	Blocks: 8          IO Block: 4096   directory
Device: 39h/57d	Inode: 514041      Links: 2
Access: (0550/dr-xr-x---)  Uid: (   33/www-data)   Gid: (   33/www-data)
Access: 2024-09-04 18:58:58.895113956 +0000
Modify: 2024-09-04 18:58:57.191090190 +0000
Change: 2024-09-04 18:58:57.191090190 +0000
 Birth: -
```

This way, the `www-data` can read from `/home/atomadm/static` and can read/write from `/mnt/atom_uploads`. 

You can upload files to SFTPGo home dir and check both bindfs mount point dirs and permissions.


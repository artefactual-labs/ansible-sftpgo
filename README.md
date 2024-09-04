# Ansible Role: SFTPGo

This Ansible role installs and configures [SFTPGo](https://github.com/drakkan/sftpgo), an advanced SFTP server with additional features such as S3-compatible object storage, Google Cloud Storage, and Azure Blob Storage support.

The role assumes the web client is going to be configured with a reverse proxy.

Additionally, it supports the use of `bindfs` to mount directories with altered permissions. This is useful in scenarios where you need to adjust the ownership or permissions of files for SFTPGo users without modifying the original filesystem. (e.g., allowing www-data to delete files)

## Requirements

- Ansible 2.9 or higher
- A target machine running a supported version of Linux (e.g., Ubuntu, CentOS)

## Role Variables

The following variables are defined in `defaults/main.yml`. Some variables are optional, and their default values are provided.

### Install packages

The role uses `ppa:sftpgo/sftpgo` repo for Ubuntu and a direct link to rpm package in github. For this last link the following variable can be used:

| Variable                          | Default Value                             | Description                                               |
|-----------------------------------|-------------------------------------------|-----------------------------------------------------------|
| `sftpgo_rpm_package_url`          | "https://github.com/drakkan/sftpgo/releases/download/v2.6.2/sftpgo-2.6.2-1.x86_64.rpm" | You can get the rpm URL from https://github.com/drakkan/sftpgo/releases  |

### Hide ansible run protected variables

| Variable                          | Default Value                             | Description                                               |
|-----------------------------------|-------------------------------------------|-----------------------------------------------------------|
| `sftpgo_no_log`                   | True                                      | Set as False to get output from tasks with passwords      |

### SFTPGo API credentials

| Variable                          | Default Value                             | Description                                                                                     |
|-----------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------|
| `sftpgo_api_auth_user`            | admin_api_user                            | API user |
| `sftpgo_api_auth_key`             | CHANGEME!PLEASE$                          | API key  |

### SFTPGo Users Configuration

| Variable                          | Default Value                             | Description                                                                                     |
|-----------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------|
| `sftpgo_users`                    | `[]`                                      | A list of users to be created in SFTPGo. Each user can have additional configuration parameters. |
| `sftpgo_path_ssh_keys`            | ""                                        | The `sftpgo_path_ssh_keys` variable specifies the directory path where SSH public key files are stored. This path is prepended to the filenames listed in public_keys_files for each user. The variable is optional, but if used, it must end with a / to correctly concatenate with the filenames. This variable is particularly useful when you already have a list of filenames for SSH keys (public_keys_files) and want to define the directory separately. By setting sftpgo_path_ssh_keys, you can avoid repeating the directory path for each key file, making your configuration cleaner and more manageable. |

#### User Configuration

Each user in `sftpgo_users` can have the following attributes:

| Attribute                         | Description                                                                                     |
|-----------------------------------|-------------------------------------------------------------------------------------------------|
| `user`                            | The username of the SFTPGo user.                                                                |
| `home_dir`                        | The home directory for the user.                                                                |
| `home_dir_perms`                  | Permissions for the user's home directory (optional, defaults to `0755`).                       |
| `password`                        | The password for the user.                                                                     |
| `create_subdirs`                  | A list of subdirectories to create within the user's home directory (optional).                |
| `subdir_perms`                    | Permissions for the subdirectories to create within the user's home directory (optional).      |
| `public_keys`                     | The `public_keys` variable is an optional list where you can specify one or more SSH public keys for the user. These keys will be used for key-based authentication. Each key should be a valid SSH public key string in a supported format (e.g., ssh-ed25519, ssh-rsa, etc.). |
|
| `public_keys_files`               | The `public_keys_files` variable is an optional list where you can specify paths to files containing SSH public keys. Each file should contain a valid SSH public key. These keys will be added to the user's authorized keys, enabling key-based authentication. This variable is useful when you prefer to store SSH keys in separate files rather than inline within your playbook. |

### Network Configuration Options

| Variable                          | Default Value                             | Description                                                                                     |
|-----------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------|
| `sftpgo_httpd_bind_port`             | `"8081"`                          | The port SFTPGo web client will bind to.                                                       |
| `sftpgo_httpd_bind_address`        | `"127.0.0.1"`                                      | The address SFTPGo web client will bind to.            |
| `sftpgo_sftpd_bind_port`    | `"33322"`                                      | The port SFTPGo web client will bind to.        |
| `sftpgo_sftpd_bind_address`    | `""`                                      | Listen in all IP addresses when empty       |


### Bindfs Configuration

This role supports the use of `bindfs` to mount directories with altered permissions. This is useful in scenarios where you need to adjust the ownership or permissions of files for SFTPGo users without modifying the original filesystem.

#### Bindfs Variables

| Variable                          | Default Value                             | Description                                                                                     |
|-----------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------|
| `sftpgo_bindfs_mounts`            | `[]`                                      | A list of `bindfs` mounts to create. Each mount is represented as a dictionary.                 |

#### Bindfs Mount Configuration

Each item in the `sftpgo_bindfs_mounts` list can have the following attributes:

| Attribute                         | Description                                                                                     |
|-----------------------------------|-------------------------------------------------------------------------------------------------|
| `source`                          | The source directory to be mounted.                                                             |
| `dest`                            | The destination directory where the source will be mounted.                                     |
| `user`                            | The user to own the files in the destination directory. Optional.                               |
| `group`                           | The group to own the files in the destination directory. Optional.                              |
| `perms`                           | The permissions to apply to the files in the destination directory. Optional.                   |
| `options`                         | Additional options to pass to `bindfs`. Optional.                                               |


## Example Playbook

Here’s an example of how to use the `ansible-sftpgo` role in your playbook:

```yaml
---
- hosts: sftp_servers
  roles:
    - role: artefactual-labs.ansible-sftpgo
      sftpgo_users:
        - user: "user1"
          home_dir: "/home/sftpgo"
          password: "user1password"
          public_keys:
            - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIFAKKEYXXXXXXXXXXXXXXXXXXXX user1@example.com"
        - user: "user2"
          home_dir: "/home/sftpgo-secure"
          home_dir_perms: "0750"
          create_subdirs:
            - "uploads"
            - "downloads"
          subdir_perms: "0550"
          password: "user2password"
          public_keys:
            - "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAICONTENTXXXXXXXXXXXXXXXXXXX user2@example.com"
```

## Example nginx reverse config settings

```
server {
  listen 8888 ssl;
  server_name example.accesstomemory.org ;
  ssl_certificate /var/lib/acme/live/example.accesstomemory.org/fullchain;
  ssl_certificate_key /var/lib/acme/live/example.accesstomemory.org/privkey;
  ssl_session_timeout 5m;
  ssl_session_cache shared:SSL:50m;
  ssl_protocols TLSv1.2 TLSv1.3;
  ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305';
  ssl_prefer_server_ciphers on;
  add_header Strict-Transport-Security max-age=63072000;
  client_max_body_size 520M;
  proxy_max_temp_file_size 1024m;

  location / {
    proxy_pass http://127.0.0.1:8081;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    }

  location /api/ {
    deny all;
    }

  location /robots.txt {
    alias /etc/nginx/robots.txt;
  }

  include /etc/nginx/badbots.conf;
}
```

Note the deny all to `/api`. It is because in role you should use the rest API without the reverse proxy

## License

This role is licensed under the GNU Affero General Public License v3.0. See the [LICENSE](LICENSE) file for more details.

## Author Information

This role was created by [Artefactual Labs](https://github.com/artefactual-labs).

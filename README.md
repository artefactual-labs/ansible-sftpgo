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

### Optional S3 virtual folders

Set `sftpgo_s3_virtual_folders` to create and update S3-backed virtual folders.
Each folder is created once in SFTPGo and can then be mounted for one or more users.
The quota defaults are defined at the folder level for a concise per-customer
configuration, although SFTPGo applies them to each user-folder mapping.

```yaml
sftpgo_s3_virtual_folders:
  - name: customer-incoming
    bucket: artefactual-ingest
    region: eu-west-1
    key_prefix: customers/customer/incoming/
    quota_size: 10 GB
    quota_files: 10000
    # For AWS, prefer an instance/task/service-account IAM role and omit both
    # access_key and access_secret.
    # access_key: "{{ vault_s3_access_key }}"
    # access_secret: "{{ vault_s3_access_secret }}"
    # endpoint: https://minio.example.org
    # force_path_style: true

sftpgo_users:
  - user: customer
    home_dir: /home/sftpgo/customer
    password: "{{ vault_customer_password }}"
    virtual_folders:
      - name: customer-incoming
        virtual_path: /incoming
        access: protected
```

`key_prefix` must not start with `/` and, when set, must end with `/`. The S3
bucket must already exist; its prefix does not need to be created.

The role validates this configuration before calling the SFTPGo API:

```yaml
# Valid: unique folder name and an absolute, non-root mount path.
sftpgo_s3_virtual_folders:
  - name: customer-incoming
    bucket: artefactual-ingest
    region: eu-west-1
    key_prefix: customers/customer/incoming/

sftpgo_users:
  - user: customer
    home_dir: /home/sftpgo/customer
    password: "{{ vault_customer_password }}"
    virtual_folders:
      - name: customer-incoming
        virtual_path: /incoming
        access: protected
```

Folder names must be unique. A user must not map the same folder name or mount
path twice. Mount paths must begin with `/` and cannot be `/` itself; for
example, `incoming` and `/` are rejected.

Each user mapping must reference a name in `sftpgo_s3_virtual_folders`. Set
`access` to one of these modes, or omit it to use the safer `protected` mode:

| Access mode | SFTPGo permissions |
|-------------|--------------------|
| `protected` (default) | list and download only; all changes are denied |
| `read-write` | all permissions, including deletion |

Use `protected` for an Archivematica AIP store: users can browse and download
AIPs, but cannot upload or otherwise alter the preserved content.

The mapping's `access` value is the only way to choose its permission model;
do not add a `permissions` field to a mapping or define `permissions` on a user
that has S3 virtual folders. The role rejects those settings and applies its
fixed profiles instead. This avoids an accidental broader permission (for
example, a nested `*` rule) overriding the read-only policy and changing
preservation data. Writable aliases to the same S3 bucket/prefix and nested
mounts below a protected path are also rejected for the same reason.

The role derives the user-folder permissions. If the user does not declare
`permissions`, users with virtual folders receive `list` permission at `/`;
users without virtual folders retain the role's existing `*` permission at
`/`. You can set `quota_size` or `quota_files` on an individual user mapping
to override the folder default. `quota_size` accepts a byte count or Ansible
size notation such as `500MB`, `10 GB`, or `1TB`; both compact and spaced unit
forms are accepted and converted to bytes before being sent to SFTPGo.
`quota_files` is always a file count. Both quota values use `0` for unlimited;
use `-1` for both values to include a private virtual folder in the user's
overall quota. Quota usage is tracked only for operations performed through
SFTPGo.

For defense in depth, use an S3 identity with list/read-only access for a
protected folder. SFTPGo permissions prevent changes through that user's SFTP
session, but do not protect data from administrators, other SFTPGo accounts,
or clients using backend credentials directly. For preservation-grade
immutability, configure the object store's retention/Object Lock controls too.
Read-write mappings need object-write and delete access.

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
| `virtual_folders`                 | Optional list of S3 virtual-folder mappings. Each mapping requires `name` and `virtual_path`; `access` defaults to `protected`. Quota values default to the matching `sftpgo_s3_virtual_folders` entry. |

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

### OIDC Auth for webclient (Optional) Configuration

This role supports OIDC auth for webclient using a `pre_login_hook` script to create the oidc users. See: [SFTPGo OpenID Connect Doc](https://docs.sftpgo.com/2.6/oidc/)

#### OIDC Auth for webclient Variables

| Variable                          | Default Value                             | Description                                                                                     |
|-----------------------------------|-------------------------------------------|-------------------------------------------------------------------------------------------------|
| `sftpgo_oidc_auth_enable`         | False                                     | Set to True to enable OIDC authentication for the web client.                                   |
| `sftpgo_oidc_client_id`           | `""`                                      | OIDC client ID.                                                                                 |
| `sftpgo_oidc_client_secret`       | `""`                                      | OIDC client secret.                                                                             |
| `sftpgo_oidc_redirect_base_url`   | `""`                                      | Base URL for OIDC redirection. If using a reverse proxy, specify its FQDN and port. Example: "https://customer.archivematica.org:8443" |
| `sftpgo_oidc_config_url`          | `""`                                      | OIDC configuration URL, excluding "/.well-known/openid-configuration". [SFTPGo OpenID Connect Doc](https://docs.sftpgo.com/2.6/oidc/) |
| `sftpgo_oidc_username_field`      | `"preferred_username"`                    | The claim in the OIDC ID token to be used as the SFTPGo username. Common values: "preferred_username", "email", or "sub". Ensure the chosen field is unique and consistent for user authentication. |
| `sftpgo_oidc_implicit_roles`      | True                                      | When enabled (True), SFTPGo will automatically assign roles based on OIDC claims. If disabled (False), roles must be explicitly assigned within SFTPGo. Useful for mapping user roles from the identity provider. |
| `sftpgo_oidc_scopes`              | `[ "openid", "profile", "email" ]`        | List of OIDC scopes requested during authentication. These define the level of access granted by the identity provider (IdP). Modify this list if additional scopes are needed based on your IdP configuration. |
| `sftpgo_oidc_debug`               | False                                     | Enable (True) or disable (False) OIDC debug logging. When enabled, additional debug logs related to OIDC authentication will be recorded to help troubleshoot login issues. Recommended to keep disabled in production to avoid excessive logging. |
| `sftpgo_oidc_pre_login_hook_file` | `"/usr/local/bin/sftpgo_pre_login_hook.py"` | Hook script to create oidc users |
| `sftpgo_oidc_user_pre_login_hook_base_directory` | `"/home/sftpgo"`           | Homedir used by oidp users |

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

## Examples

The role is highly flexible, especially with permissions and BindFS settings. Below are detailed scenarios that demonstrate how to handle SFTPGo deployment and share home directories with other applications:

* [AtoM VM with `static` and `atom_uploads` directories used by AtoM](documentation/AtoM_example.md)
* [Archivematica VM with `transfer_source` and  AIP/DIP Store directories used by Archivematica](documentation/AM_example.md)

## License

This role is licensed under the GNU Affero General Public License v3.0. See the [LICENSE](LICENSE) file for more details.

## Author Information

This role was created by [Artefactual Labs](https://github.com/artefactual-labs).

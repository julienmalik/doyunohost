Deployment Script
-----------------

Prerequisites
-------------

* python-requests (Debian or Ubuntu apt-get install python-requests)
* A Digital Ocean account
* Some credits owned
* An SSH key configured and added to Digital Ocean (highly recommended)
* An API key ( https://www.digitalocean.com/api_access )


Usage
-----

```bash
deploy.py --client-id <my_client_id>     # DO client ID
          --api-key <my_api_key>         # DO API key
          --domain <mydomain.nohost.me>  # Domain name
          [--password <my_password>]     # Admin password (auto-execute post-installation if set)
          [--no-ssh-key-auth]            # Do not use SSH Key based authentatication
          [--test]                       # Install from test repository
          [--no-snapshot]                # Do not snapshot after installation nor recover from snapshot
```

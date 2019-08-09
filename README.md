# Kubernetes Collection for Ansible

[![Build Status](https://travis-ci.com/geerlingguy/ansible-collection-k8s.svg?branch=master)](https://travis-ci.com/geerlingguy/ansible-collection-k8s)

This collection contains Kubernetes-related roles and Ansible plugins and modules maintained by Jeff Geerling (geerlingguy).

It includes:

  - [geerlingguy.kubernetes](https://github.com/geerlingguy/ansible-role-kubernetes)
  - [geerlingguy.k8s_manifests](https://github.com/geerlingguy/ansible-role-k8s_manifests)

## Usage

Install this collection locally:

    ansible-galaxy collection install geerlingguy.k8s -p ./collections

Then you can use the roles from the collection in your playbooks:

    ---
    - hosts: all
    
      collections:
        - geerlingguy.k8s
    
      roles:
        - kubernetes
        - role: k8s_manifests
          vars:
            k8s_manifests_base_dir: ''
            k8s_manifests:
              - monitoring/prometheus
              - dir: docker-registry
                namespace: registry

> If you want to be more explicit, you can use the fully-qualified role name when referring to a role in this collection, like `geerlingguy.k8s.kubernetes` instead of just `kubernetes`. This could be helpful if, for example, you maintain a separate `kubernetes` role in another place on your local workstation.

## Development

Currently, all the Kubernetes roles (inside `roles/`) are Git submodules, and work on the roles themselves should take place in the upstream Role repository. At some point, the roles might move into this repository for their canonical home.

This collection has some integration tests (inside `tests/`), however, which pull all the roles together and ensure they work in tandem on the latest supported platforms.

TODO: Instructions for running tests.

### Pushing a new version

Currently the process of building and pushing a new version artifact to Galaxy is manual. This process will be automated based on tags/releases via Travis CI soon, but for now, here is how to release a new version:

  1. Make sure the `version` string in `galaxy.yml` matches the version of the collection you wish to publish (should correspond to the latest Git tag).
  2. Build the collection artifact: `ansible-galaxy collection build`
  3. Publish the collection artifact: `ansible-galaxy collection publish ./geerlingguy-k8s-1.2.3.tar.gz --api-key=[key goes here]`

> Note: The above commands require Ansible 2.9 (Ansible's `devel` branch as of mid-2019) or later.

## Author

This collection was created in 2019 by [Jeff Geerling](https://www.jeffgeerling.com/), author of [Ansible for DevOps](https://www.ansiblefordevops.com/) and [Ansible for Kubernetes](https://www.ansibleforkubernetes.com).

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

This collection has some integration tests (inside `molecule/`), however, which pull all the roles together and ensure they work in tandem on the latest supported platforms.

To run a particular test scenario, you need to install molecule and the OpenShift Python client (`pip install molecule openshift`), then you can run:

    molecule test -s [scenario]

For example, to run the k8s_manifests role test scenario:

    molecule test -s test-manifests

If you would like to develop the collection or leave a scenario running for debugging, use `molecule converge` to run the scenario but not tear down the local test environment.

### Pushing a new version

Before tagging a new version, make sure all the git submodules are up to date:

    git submodule update --recursive --remote

Then commit and push all changes, and make sure all tests are passing.

Then tag the new version of the collection and push the tag.

Once pushed, if tests pass, Travis CI will deploy the new collection version using the playbook in `scripts/deploy.yml`. That directory also contains the `galaxy.yml` template that will be used to build the collection metadata.

## Author

This collection was created in 2019 by [Jeff Geerling](https://www.jeffgeerling.com/), author of [Ansible for DevOps](https://www.ansiblefordevops.com/) and [Ansible for Kubernetes](https://www.ansibleforkubernetes.com).

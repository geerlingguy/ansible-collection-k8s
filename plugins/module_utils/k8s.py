#
#  Copyright 2018 Red Hat | Ansible
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function

import copy
from datetime import datetime
from distutils.version import LooseVersion
import time
import sys
import traceback

from ansible.module_utils.basic import missing_required_lib
from ansible.module_utils.k8s.common import AUTH_ARG_SPEC, COMMON_ARG_SPEC
from ansible.module_utils.six import string_types
from ansible.module_utils.k8s.common import KubernetesAnsibleModule
from ansible.module_utils.k8s.raw import KubernetesRawModule
from ansible.module_utils.common.dict_transformations import dict_merge
from ansible.parsing.dataloader import DataLoader
from ansible.template import Templar


try:
    import yaml
    from openshift.dynamic.exceptions import DynamicApiError, NotFoundError, ConflictError, ForbiddenError, KubernetesValidateMissing
except ImportError:
    # Exceptions handled in common
    pass

try:
    import kubernetes_validate
    HAS_KUBERNETES_VALIDATE = True
except ImportError:
    HAS_KUBERNETES_VALIDATE = False

K8S_CONFIG_HASH_IMP_ERR = None
try:
    from openshift.helper.hashes import generate_hash
    HAS_K8S_CONFIG_HASH = True
except ImportError:
    K8S_CONFIG_HASH_IMP_ERR = traceback.format_exc()
    HAS_K8S_CONFIG_HASH = False


class KubernetesTemplateModule(KubernetesRawModule):

    @property
    def argspec(self):
        argument_spec = copy.deepcopy(COMMON_ARG_SPEC)
        argument_spec.update(copy.deepcopy(AUTH_ARG_SPEC))
        argument_spec['template'] = dict(type='path')
        argument_spec['merge_type'] = dict(type='list', choices=['json', 'merge', 'strategic-merge'])
        argument_spec['wait'] = dict(type='bool', default=False)
        argument_spec['wait_timeout'] = dict(type='int', default=120)
        argument_spec['wait_condition'] = dict(type='dict', default=None, options=self.condition_spec)
        argument_spec['validate'] = dict(type='dict', default=None, options=self.validate_spec)
        argument_spec['append_hash'] = dict(type='bool', default=False)
        argument_spec['apply'] = dict(type='bool')
        return argument_spec

    def __init__(self, k8s_kind=None, *args, **kwargs):
        self.client = None
        self.warnings = []

        mutually_exclusive = [
            ('resource_definition', 'src'),
            ('merge_type', 'apply'),
        ]

        KubernetesAnsibleModule.__init__(self, *args,
                                         mutually_exclusive=mutually_exclusive,
                                         supports_check_mode=True,
                                         **kwargs)
        self.kind = k8s_kind or self.params.get('kind')
        self.api_version = self.params.get('api_version')
        self.name = self.params.get('name')
        self.namespace = self.params.get('namespace')
        resource_definition = self.params.get('resource_definition')
        validate = self.params.get('validate')
        if validate:
            if LooseVersion(self.openshift_version) < LooseVersion("0.8.0"):
                self.fail_json(msg="openshift >= 0.8.0 is required for validate")
        self.append_hash = self.params.get('append_hash')
        if self.append_hash:
            if not HAS_K8S_CONFIG_HASH:
                self.fail_json(msg=missing_required_lib("openshift >= 0.7.2", reason="for append_hash"),
                               exception=K8S_CONFIG_HASH_IMP_ERR)
        if self.params['merge_type']:
            if LooseVersion(self.openshift_version) < LooseVersion("0.6.2"):
                self.fail_json(msg=missing_required_lib("openshift >= 0.6.2", reason="for merge_type"))
        if self.params.get('apply') is not None:
            if LooseVersion(self.openshift_version) < LooseVersion("0.9.0"):
                self.fail_json(msg=missing_required_lib("openshift >= 0.9.0", reason="for apply"))
            self.apply = self.params['apply']
        else:
            self.apply = LooseVersion(self.openshift_version) >= LooseVersion("0.9.0")

        if resource_definition:
            if isinstance(resource_definition, string_types):
                try:
                    self.resource_definitions = yaml.safe_load_all(resource_definition)
                except (IOError, yaml.YAMLError) as exc:
                    self.fail(msg="Error loading resource_definition: {0}".format(exc))
            elif isinstance(resource_definition, list):
                self.resource_definitions = resource_definition
            else:
                self.resource_definitions = [resource_definition]

        template = self.params.get('template')
        if template:
            self.resource_definitions = self.load_resource_definitions(template)

        src = self.params.get('src')
        if src and not template:
            self.resource_definitions = self.load_resource_definitions(src)

        if not resource_definition and not src and not template:
            implicit_definition = dict(
                kind=self.kind,
                apiVersion=self.api_version,
                metadata=dict(name=self.name)
            )
            if self.namespace:
                implicit_definition['metadata']['namespace'] = self.namespace
            self.resource_definitions = [implicit_definition]

    def execute_module(self):
        changed = False
        results = []
        self.client = self.get_api_client()

        flattened_definitions = []
        for definition in self.resource_definitions:
            # For templates, template each definition before applying it.
            template = self.params.get('template')
            if template:
                # TODO: Is there a way we can get all the available vars, e.g.
                # via action plugin or something, to pass to Templar()?
                all_vars = {
                    "test_key": "test-value",
                }
                loader = DataLoader()
                definition = Templar(loader=loader, variables=all_vars).template(definition)

            kind = definition.get('kind', self.kind)
            api_version = definition.get('apiVersion', self.api_version)
            if kind.endswith('List'):
                resource = self.find_resource(kind, api_version, fail=False)
                flattened_definitions.extend(self.flatten_list_kind(resource, definition))
            else:
                resource = self.find_resource(kind, api_version, fail=True)
                flattened_definitions.append((resource, definition))

        for (resource, definition) in flattened_definitions:
            kind = definition.get('kind', self.kind)
            api_version = definition.get('apiVersion', self.api_version)
            definition = self.set_defaults(resource, definition)
            self.warnings = []
            if self.params['validate'] is not None:
                self.warnings = self.validate(definition)
            result = self.perform_action(resource, definition)
            result['warnings'] = self.warnings
            changed = changed or result['changed']
            results.append(result)

        if len(results) == 1:
            self.exit_json(**results[0])

        self.exit_json(**{
            'changed': changed,
            'result': {
                'results': results
            }
        })

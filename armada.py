# -*- coding: utf-8 -*-

import copy
import re

import requests
import uritemplate


class FleetClient(object):
    """
    A Fleet API client.
    """
    def __init__(self, url=None):
        self.url = url if url else 'http://localhost:8080/fleet/v1'
        self._discovery = self._discover()
        self._resources = []
        self._build()

    def _discover(self):
        self._discovery_url = '{}/discovery'.format(self.url)
        response = requests.get(self._discovery_url)
        return response.json()

    @property
    def resources(self):
        return self._resources

    @property
    def version(self):
        return self._discovery.get('version')

    def _build(self):
        for resource, interface in self._discovery.get('resources').items():
            resource = FleetResource(resource)
            methods = interface.get('methods')

            for method, contract in methods.items():
                path = contract.get('path')
                endpoint = '{}/{}'.format(self.url, path)
                resource._create_and_attach_method(method, endpoint, contract)

            self._resources.append(resource)

        for resource in self._resources:
            setattr(self, camel_to_snake_case(resource.name), resource)


class FleetResource(object):
    def __init__(self, name):
        self.name = name

    def _create_method(self, endpoint, contract):
        def api_request(**kwargs):
            http_method = contract.get('httpMethod')
            headers = {'Content-Type': 'application/json'}
            payload = copy.copy(kwargs)

            # Expand the URI template to construct the final URL.
            url = uritemplate.expand(endpoint, payload)

            for param_name, param_spec in contract.get('parameters').items():
                # If the parameter is part of the URL, remove it from the query
                # string.
                if (param_spec.get('location') == 'path' and
                        param_name in payload):
                    del payload[param_name]

            return requests.request(http_method, url, headers=headers,
                                    params=payload)

        new_method = api_request
        new_method.__doc__ = contract.get('description')

        return new_method

    def _attach_method(self, name, method):
        setattr(self, name, method)

    def _create_and_attach_method(self, name, endpoint, contract):
        name = camel_to_snake_case(name)
        method = self._create_method(endpoint, contract)
        setattr(self, name, method)


def camel_to_snake_case(name):
    """
    Convert a name in CamelCase to snake_case.
    """
    return re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name).lower()

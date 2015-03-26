# -*- coding: utf-8 -*-

import copy
import re
import types

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
                resource._add_method(method, endpoint, contract)

            self._resources.append(resource)

        for resource in self._resources:
            setattr(self, camel_to_snake_case(resource.name), resource)


class FleetResource(object):
    def __init__(self, name):
        self.name = name

    def _add_method(self, name, endpoint, contract):
        name = str(camel_to_snake_case(name))

        def method(self, *args, **kwargs):
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

        method.__doc__ = contract.get('description')
        method.__name__ = name

        # Construct an empty class to hold the method.
        cls = types.ClassType(str(self.name), (object,), {})

        setattr(self, name, types.MethodType(method, self, cls))


def camel_to_snake_case(name):
    """
    Convert a name in CamelCase to snake_case.
    """
    return re.sub(r'(.)([A-Z][a-z]+)', r'\1_\2', name).lower()

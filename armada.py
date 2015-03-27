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
            param_schema = contract.get('parameters')

            # Construct a set of utility dictionaries to map data between
            # the Python binding's keyword arguments and the mixedCase
            # parameters used in the Fleet API service description.
            #
            # Map schema parameters to Python-style keyword arguments, and vice
            # versa.
            params_to_kwargs = dict((p, camel_to_snake_case(p))
                                    for p in param_schema.keys())
            kwargs_to_params = dict((k, p)
                                    for (p, k) in params_to_kwargs.items())
            # Construct the equivalent dictionary of API parameter values from
            # the keyword arguments.
            params = dict((p, kwargs.get(k)) for (p, k) in params_to_kwargs.items())

            # Expand the URI template to construct the final URL.
            url = uritemplate.expand(endpoint, params)

            # Track required parameters.
            # We cannot change the method signature at runtime to require
            # positional arguments. Handle keyword arguments instead.
            required_kwargs = []
            for param_name, param_spec in param_schema.items():
                required = param_spec.get('required', False)
                if required:
                    required_kwargs.append(params_to_kwargs[param_name])
            validate_required_kwargs(kwargs, required_kwargs)

            for param_name, param_spec in param_schema.items():
                # If the parameter is part of the URL, remove it from the query
                # string.
                if (param_spec.get('location') == 'path' and param_name in params):
                    del params[param_name]

            return requests.request(http_method, url, headers=headers,
                                    params=params)

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


def validate_required_kwargs(kwargs, required_kwargs=None):
    """
    Validates required keyword arguments.

    Args:
        kwargs (dict): Keyword arguments.
        required_kwargs (list): Required keyword arguments.

    Raises:
        TypeError: One or more required keyword arguments is missing.
    """
    if not required_kwargs:
        return

    missing_kwargs = [k for k in required_kwargs if k not in kwargs]
    if not missing_kwargs:
        return

    plural = 's' if len(missing_kwargs) > 1 else ''
    raise TypeError("missing {} required keyword argument{}: {}".format(
        len(missing_kwargs), plural,
        ', '.join(("'{}'".format(k) for k in missing_kwargs)),
    ))

# -*- coding: utf-8 -*-

import re
import textwrap
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

        def method(self, *args, **kwargs):
            # Construct the equivalent dictionary of API parameter values from
            # the keyword arguments.
            params = dict((p, kwargs.get(k)) for (p, k) in params_to_kwargs.items())

            # We cannot change the method signature at runtime to require
            # specific positional arguments. We can fake it, however:
            # the API suggests required parameters.
            required_params = contract.get('parameterOrder', ())
            # Join positional arguments with the rest of the keyword-based
            # parameters.
            for param_name, param_value in zip(required_params, args):
                params[param_name] = param_value

            validate_args(name, args, required_params)

            # Expand the URI template to construct the final URL.
            url = uritemplate.expand(endpoint, params)

            for param_name, param_spec in param_schema.items():
                # If the parameter is part of the URL, remove it from the query
                # string.
                if (param_spec.get('location') == 'path' and param_name in params):
                    del params[param_name]

            return requests.request(http_method, url, headers=headers,
                                    params=params)

        name = str(camel_to_snake_case(name))
        http_method = contract.get('httpMethod')
        headers = {'Content-Type': 'application/json'}

        # Construct a set of utility dictionaries to map data between the
        # Python binding's keyword arguments and the mixedCase parameters used
        # in the Fleet API service description.
        param_schema = contract.get('parameters')
        params_to_kwargs = dict((p, camel_to_snake_case(p))
                                for p in param_schema.keys())
        kwargs_to_params = dict((k, p)
                                for (p, k) in params_to_kwargs.items())

        # Finally, Pythonize the parameter schema to construct nice docstrings.
        docstring_parameters= dict((params_to_kwargs[k], v)
                                    for k, v in param_schema.items())
        docstring = Docstring(contract.get('description'),
                              parameters=docstring_parameters,
                              returns=requests.Response)
        method.__doc__ = str(docstring)
        method.__name__ = name

        # Construct an empty, named class to hold the method.
        cls = types.ClassType(str(self.name), (object,), {})

        setattr(self, name, types.MethodType(method, self, cls))


class Docstring(object):
    """
    Representation of a Python docstring.
    """

    class Parameter(object):
        """
        A function parameter.

        Args:
            name (str): Parameter name (e.g., unit_name).
            type (callable): Parameter type (e.g., `str`, `int`).
            required (bool): Whether the parameter is a positional argument
                (True) or a keyword argument (False).
        """

        # Match JSON schema types to native Python types.
        SCHEMA_TYPES = {
            'array': list,
            'string': str,
        }

        def __init__(self, name, type, required=True):
            self.name = name
            self.type = type
            self.required = required

        @classmethod
        def from_schema(cls, name, schema):
            name = name
            type = cls.SCHEMA_TYPES.get(schema.get('type'))
            required = schema.get('required')
            return cls(name, type, required)

        def __str__(self):
            type_ = self.type.__name__
            if not self.required:
                type_ = '{}, optional'.format(type_)
            return '{} ({})'.format(self.name, type_)


    def __init__(self, description, parameters=None, returns=None, indent=4):
        self.description = description
        self.parameters = [self.Parameter.from_schema(name, schema)
                           for name, schema in parameters.items()]
        self.returns = returns
        self.indent = indent
        initial_indent = self.indent * ' '
        subsequent_indent = 2 * initial_indent
        self._wrapper = textwrap.TextWrapper(initial_indent=initial_indent,
                                             subsequent_indent=subsequent_indent)

    def __str__(self):
        """
        Represent the docstring in Google format.
        """
        docstring = [self.description]
        if self.parameters:
            arg_lines = ['Args:']
            for parameter in self.parameters:
                arg_lines.extend(self._wrapper.wrap(str(parameter)))
            docstring.append('\n'.join(arg_lines))
        if self.returns:
            return_lines = ['Returns:']
            return_type = self.returns.__name__
            return_lines.extend(self._wrapper.wrap(return_type))
            docstring.append('\n'.join(return_lines))
        return '\n\n'.join(docstring)


def camel_to_snake_case(name):
    """
    Convert a name in CamelCase or mixedCase to snake_case.
    """
    # By nickl- on StackOverflow: <http://stackoverflow.com/a/12867228>.
    return re.sub(r'((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))', r'_\1', name).lower()


def validate_args(name, args, required_args):
    """
    Validate the number of positional arguments.

    Duplicates the behaviour of functions with stable signatures.

    Args:
        name (str): Function name.
        args (tuple, list): Positional arguments to validate.
        required_args (tuple, list): Required arguments.

    Raises:
        TypeError: The number of positional arguments does not match the
            required number.
    """
    if len(args) == len(required_args):
        return
    superlative = 'most' if len(args) > len(required_args) else 'least'
    plural = 's' if len(required_args) > 1 else ''
    raise(TypeError('{}() takes at {} {} argument{} ({} given)'.format(
        name, superlative, len(required_args), plural, len(args)
    )))

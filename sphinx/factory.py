# -*- coding: utf-8 -*-
"""
    sphinx.factory
    ~~~~~~~~~~~~~~

    Sphinx component factory.

    Gracefully adapted from the TextPress system by Armin.

    :copyright: Copyright 2007-2016 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""
from __future__ import print_function

from pkg_resources import iter_entry_points
from six import itervalues

from sphinx.errors import ExtensionError, SphinxError
from sphinx.domains import ObjType
from sphinx.domains.std import GenericObject, Target
from sphinx.extension import load_extension
from sphinx.locale import _
from sphinx.roles import XRefRole
from sphinx.util.docutils import directive_helper

if False:
    # For type annotation
    from typing import Any, Callable, Dict, Iterator, List, Type  # NOQA
    from docutils import nodes  # NOQA
    from docutils.parsers import Parser  # NOQA
    from sphinx.application import Sphinx  # NOQA
    from sphinx.builders import Builder  # NOQA
    from sphinx.domains import Domain, Index  # NOQA
    from sphinx.environment import BuildEnvironment  # NOQA


class SphinxFactory(object):
    def __init__(self):
        self.builders = {}          # type: Dict[unicode, Type[Builder]]
        self.domains = {}           # type: Dict[unicode, Type[Domain]]
        self.source_parsers = {}    # type: Dict[unicode, Parser]

    def add_builder(self, builder):
        # type: (Type[Builder]) -> None
        if not hasattr(builder, 'name'):
            raise ExtensionError(_('Builder class %s has no "name" attribute') % builder)
        if builder.name in self.builders:
            raise ExtensionError(_('Builder %r already exists (in module %s)') %
                                 (builder.name, self.builders[builder.name].__module__))
        self.builders[builder.name] = builder

    def preload_builder(self, app, name):
        # type: (Sphinx, unicode) -> None
        if name is None:
            return

        if name not in self.builders:
            entry_points = iter_entry_points('sphinx.builders', name)
            try:
                entry_point = next(entry_points)
            except StopIteration:
                raise SphinxError(_('Builder name %s not registered or available'
                                    ' through entry point') % name)
            load_extension(app, entry_point.module_name)

    def create_builder(self, app, name):
        # type: (Sphinx, unicode) -> Builder
        if name not in self.builders:
            raise SphinxError(_('Builder name %s not registered') % name)

        return self.builders[name](app)

    def add_domain(self, domain):
        # type: (Type[Domain]) -> None
        if domain.name in self.domains:
            raise ExtensionError(_('domain %s already registered') % domain.name)
        self.domains[domain.name] = domain

    def has_domain(self, domain):
        # type: (unicode) -> bool
        return domain in self.domains

    def create_domains(self, env):
        # type: (BuildEnvironment) -> Iterator[Domain]
        for DomainClass in itervalues(self.domains):
            yield DomainClass(env)

    def override_domain(self, domain):
        # type: (Type[Domain]) -> None
        if domain.name not in self.domains:
            raise ExtensionError(_('domain %s not yet registered') % domain.name)
        if not issubclass(domain, self.domains[domain.name]):
            raise ExtensionError(_('new domain not a subclass of registered %s '
                                   'domain') % domain.name)
        self.domains[domain.name] = domain

    def add_directive_to_domain(self, domain, name, obj,
                                has_content=None, argument_spec=None, **option_spec):
        # type: (unicode, unicode, Any, bool, Any, Any) -> None
        if domain not in self.domains:
            raise ExtensionError(_('domain %s not yet registered') % domain)
        directive = directive_helper(obj, has_content, argument_spec, **option_spec)
        self.domains[domain].directives[name] = directive

    def add_role_to_domain(self, domain, name, role):
        # type: (unicode, unicode, Any) -> None
        if domain not in self.domains:
            raise ExtensionError(_('domain %s not yet registered') % domain)
        self.domains[domain].roles[name] = role

    def add_index_to_domain(self, domain, index):
        # type: (unicode, Type[Index]) -> None
        if domain not in self.domains:
            raise ExtensionError(_('domain %s not yet registered') % domain)
        self.domains[domain].indices.append(index)

    def add_object_type(self, directivename, rolename, indextemplate='',
                        parse_node=None, ref_nodeclass=None, objname='',
                        doc_field_types=[]):
        # type: (unicode, unicode, unicode, Callable, nodes.Node, unicode, List) -> None
        # create a subclass of GenericObject as the new directive
        directive = type(directivename,  # type: ignore
                         (GenericObject, object),
                         {'indextemplate': indextemplate,
                          'parse_node': staticmethod(parse_node),  # type: ignore
                          'doc_field_types': doc_field_types})

        stddomain = self.domains['std']
        stddomain.directives[directivename] = directive
        stddomain.roles[rolename] = XRefRole(innernodeclass=ref_nodeclass)
        stddomain.object_types[directivename] = ObjType(objname or directivename, rolename)

    def add_crossref_type(self, directivename, rolename, indextemplate='',
                          ref_nodeclass=None, objname=''):
        # type: (unicode, unicode, unicode, nodes.Node, unicode) -> None
        # create a subclass of Target as the new directive
        directive = type(directivename,  # type: ignore
                         (Target, object),
                         {'indextemplate': indextemplate})

        stddomain = self.domains['std']
        stddomain.directives[directivename] = directive
        stddomain.roles[rolename] = XRefRole(innernodeclass=ref_nodeclass)
        stddomain.object_types[directivename] = ObjType(objname or directivename, rolename)

    def add_source_parser(self, suffix, parser):
        # type: (unicode, Parser) -> None
        if suffix in self.source_parsers:
            raise ExtensionError(_('source_parser for %r is already registered') % suffix)
        self.source_parsers[suffix] = parser

    def get_source_parsers(self):
        # type: () -> Dict[unicode, Parser]
        return self.source_parsers

# -*- coding: utf-8 -*-
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

sys.path.insert(0, os.path.abspath('../..'))
sys.path.insert(0, os.path.abspath('../'))
# -- General configuration ----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = [
    'openstackdocstheme',
    'sphinx.ext.autodoc',
    'ext.versioned_notifications',
    'oslo_config.sphinxconfiggen',
    'oslo_config.sphinxext',
    'oslo_policy.sphinxpolicygen',
    'oslo_policy.sphinxext',
]

config_generator_config_file = [
    ('../../etc/masakari/masakari-config-generator.conf',
     '_static/masakari'),
    ('../../etc/masakari/masakari-customized-recovery-flow-config-generator.conf',
     '_static/masakari-custom-recovery-methods'),
]
sample_config_basename = '_static/masakari'

policy_generator_config_file = [
    ('../../etc/masakari/masakari-policy-generator.conf', '_static/masakari'),
]
sample_policy_basename = '_static/masakari'

# autodoc generation is a bit aggressive and a nuisance when doing heavy
# text edit cycles.
# execute "export SPHINX_DEBUG=1" in your terminal to disable

# The suffix of source filenames.
source_suffix = '.rst'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = 'masakari'
copyright = '2016, OpenStack Foundation'

# If true, '()' will be appended to :func: etc. cross-reference text.
add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = True

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'native'

# -- Options for HTML output --------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
# html_theme_path = ["."]
# html_theme = '_theme'
# html_static_path = ['static']
html_theme = 'openstackdocs'

# openstackdocstheme optionns
openstackdocs_repo_name = 'openstack/masakari'
openstackdocs_bug_project = 'masakari'
openstackdocs_auto_name = False

# Output file base name for HTML help builder.
htmlhelp_basename = '%sdoc' % project

# -- Options for LaTeX output -------------------------------------------------

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass
# [howto/manual]).
latex_documents = [
    ('index',
     'doc-%s.tex' % project,
     '%s Documentation' % project,
     'OpenStack Foundation', 'manual'),
]

# Disable usage of xindy https://bugzilla.redhat.com/show_bug.cgi?id=1643664
latex_use_xindy = False

# Disable smartquotes, they don't work in latex
smartquotes_excludes = {'builders': ['latex']}

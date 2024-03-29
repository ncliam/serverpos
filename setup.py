#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
from glob import glob
from setuptools import find_packages, setup
from os.path import join, dirname


execfile(join(dirname(__file__), 'openerp', 'release.py'))  # Load release variables
lib_name = 'openerp'


def py2exe_datafiles():
    data_files = {}
    data_files['Microsoft.VC90.CRT'] = glob('C:\Microsoft.VC90.CRT\*.*')

    for root, dirnames, filenames in os.walk('openerp'):
        for filename in filenames:
            if not re.match(r'.*(\.pyc|\.pyo|\~)$', filename):
                data_files.setdefault(root, []).append(join(root, filename))

    import babel
    data_files['babel/localedata'] = glob(join(dirname(babel.__file__), 'localedata', '*'))
    others = ['global.dat', 'numbers.py', 'support.py', 'plural.py']
    data_files['babel'] = map(lambda f: join(dirname(babel.__file__), f), others)
    others = ['frontend.py', 'mofile.py']
    data_files['babel/messages'] = map(lambda f: join(dirname(babel.__file__), 'messages', f), others)

    import pytz
    tzdir = dirname(pytz.__file__)
    for root, _, filenames in os.walk(join(tzdir, 'zoneinfo')):
        base = join('pytz', root[len(tzdir) + 1:])
        data_files[base] = [join(root, f) for f in filenames]

    import docutils
    dudir = dirname(docutils.__file__)
    for root, _, filenames in os.walk(dudir):
        base = join('docutils', root[len(dudir) + 1:])
        data_files[base] = [join(root, f) for f in filenames if not f.endswith(('.py', '.pyc', '.pyo'))]

    import passlib
    pl = dirname(passlib.__file__)
    for root, _, filenames in os.walk(pl):
        base = join('passlib', root[len(pl) + 1:])
        data_files[base] = [join(root, f) for f in filenames if not f.endswith(('.py', '.pyc', '.pyo'))]

    return data_files.items()


def py2exe_options():
    if os.name == 'nt':
        import py2exe
        return {
            'console': [
                {'script': 'odoo.py'},
                {'script': 'openerp-gevent'},
                {'script': 'openerp-server', 'icon_resources': [
                    #(1, join('setup', 'win32', 'static', 'pixmaps', 'openerp-icon.ico'))
                ]},
            ],
            'options': {
                'py2exe': {
                    'skip_archive': 1,
                    'optimize': 0,  # Keep the assert running as the integrated tests rely on them.
                    'dist_dir': 'dist',
                    'packages': [
                        'asynchat', 'asyncore',
                        'commands',
                        'dateutil',
                        'decimal',
                        'decorator',
                        'docutils',
                        'email',
                        'encodings',
                        'HTMLParser',
                        'imaplib',
                        'jinja2',
                        'lxml', 'lxml._elementpath', 'lxml.builder', 'lxml.etree', 'lxml.objectify',
                        'mako',
                        'markupsafe',
                        'mock',
                        'openerp',
                        'openid',
                        'passlib',
                        'PIL',
                        'poplib',
                        'psutil',
                        'pychart',
                        'pydot',
                        'pyparsing',
                        'pyPdf',
                        'pytz',
                        'reportlab',
                        'requests',
                        'select',
                        'simplejson',
                        'smtplib',
                        'uuid',
                        'vatnumber',
                        'vobject',
                        'win32service', 'win32serviceutil',
                        'xlwt',
                        'xml', 'xml.dom',
                        'yaml',
                    ],
                    'excludes': ['Tkconstants', 'Tkinter', 'tcl'],
					"dll_excludes": ["MSVCP90.dll","libzmq.pyd","geos_c.dll", "api-ms-win-core-delayload-l1-1-1.dll",
									"api-ms-win-security-activedirectoryclient-l1-1-0.dll",
									"api-ms-win-core-rtlsupport-l1-2-0.dll",
									"api-ms-win-core-string-l1-1-0.dll","api-ms-win-core-registry-l1-1-0.dll",
									"api-ms-win-core-errorhandling-l1-1-1.dll","api-ms-win-core-string-l2-1-0.dll",
									"api-ms-win-core-profile-l1-1-0.dll","api-ms-win*.dll",
									"api-ms-win-core-processthreads-l1-1-2.dll","api-ms-win-core-libraryloader-l1-2-1.dll",
									"api-ms-win-core-file-l1-2-1.dll","api-ms-win-security-base-l1-2-0.dll",
									"api-ms-win-eventing-provider-l1-1-0.dll","api-ms-win-core-heap-l2-1-0.dll",
									"api-ms-win-core-libraryloader-l1-2-0.dll","api-ms-win-core-localization-l1-2-1.dll",
									"api-ms-win-core-sysinfo-l1-2-1.dll","api-ms-win-core-synch-l1-2-0.dll","api-ms-win-core-heap-l1-2-0.dll",
									"api-ms-win-core-handle-l1-1-0.dll","api-ms-win-core-io-l1-1-1.dll","api-ms-win-core-com-l1-1-1.dll",
									"api-ms-win-core-memory-l1-1-2.dll","api-ms-win-core-version-l1-1-1.dll","api-ms-win-core-version-l1-1-0.dll"]
                }
            },
            'data_files': py2exe_datafiles()
        }
    else:
        return {}


setup(
    name='odoo',
    version=version,
    description=description,
    long_description=long_desc,
    url=url,
    author=author,
    author_email=author_email,
    classifiers=filter(None, classifiers.split('\n')),
    license=license,
    scripts=['openerp-server', 'openerp-gevent', 'odoo.py'],
    packages=find_packages(),
    package_dir={'%s' % lib_name: 'openerp'},
    include_package_data=True,
    install_requires=[
        'babel >= 1.0',
        'decorator',
        'docutils',
        'feedparser',
        'gevent',
        'Jinja2',
        'lxml',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'mako',
        'mock',
        'passlib',
        'pillow',  # windows binary http://www.lfd.uci.edu/~gohlke/pythonlibs/
        'psutil',  # windows binary code.google.com/p/psutil/downloads/list
        'psycogreen',
        'psycopg2 >= 2.2',
        'python-chart',
        'pydot',
        'pyparsing < 2',
        'pypdf',
        'pyserial',
        'python-dateutil',
        'python-ldap',  # optional
        'python-openid',
        'pytz',
        'pyusb >= 1.0.0b1',
        'pyyaml',
        'qrcode',
        'reportlab',  # windows binary pypi.python.org/pypi/reportlab
        'requests',
        'simplejson',
        'unittest2',
        'vatnumber',
        'vobject',
        'werkzeug',
        'xlwt',
    ],
    extras_require={
        'SSL': ['pyopenssl'],
    },
    tests_require=[
        'unittest2',
        'mock',
    ],
    **py2exe_options()
)

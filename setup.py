#!/usr/bin/env python


from __future__ import print_function
from distutils.core import setup, Extension, Command
from distutils.command.build_ext import build_ext
import numpy.distutils.misc_util
import os
import os.path
import glob
import sys
import shutil


class _DocumentCommand(Command):
    user_options = [
        ('clean', 'c', 'clean'),
        ('aspell', 'a', 'run aspell')]

    def initialize_options(self):
        self._dir = os.getcwd()
        self.aspell = False
        self.clean = False

    def finalize_options(self):
        pass

    def run(self):
        try:            
            shutil.copy('README.txt', 'docs/')
            shutil.copy('README.txt', 'docs/source/')

            for f_name in glob.glob('../performance_tests/*.py'):
                shutil.copy(f_name, 'source/')

            os.chdir('docs')

            if self.clean:
                os.system('make clean')
            os.system('make html')
                    
            for f_name in glob.iglob('*.html'):
                os.system("perl -p -i -e 's/pypi\/dagpype/pypi/DAGPype/g' %s" % f_name)

            if self.aspell:
                for f_name in glob.iglob('*.html'):
                    os.system('aspell check %s' % f_name)

            os.system('cp -r build/html/* .')
            os.system('cp source/*.txt .')
            os.system('cp source/*.csv .')
            os.system('cp source/*.xml .')
            
            if os.path.exists('docs.zip'):
                os.remove('docs.zip')
            os.system('zip -r docs.zip *')
        finally:        
            os.chdir('..')


class _TestCommand(Command):
    user_options = []

    def initialize_options(self):
        self._dir = os.getcwd()

    def finalize_options(self):
        pass

    def run(self):
        try:
            os.chdir('tests')
            run_str = '%s __init__.py' % ('python3' if sys.version_info.major >= 3 else 'python')
            os.system(run_str)
        finally:        
            os.chdir('..')


class _PerformanceTestCommand(Command):
    user_options = [
        ('no-clean', 'n', 'no clean')]

    def initialize_options(self):
        self._dir = os.getcwd()
        self.no_clean = False

    def finalize_options(self):
        pass

    def run(self):
        try:
            os.chdir('performance_tests')

            os.system('swig -python corr.i')
            os.system('gcc -fPIC -O2 corr.c corr_wrap.c -I /usr/include/python2.7 -shared -o _c_corr.so')
            os.system('%s -OO __init__.py' % ('python3' if sys.version_info.major >= 3 else 'python'))

            os.system('mv *.png ../docs/source')
            
            if not self.no_clean:
                os.system('rm *.so')
                os.system('rm *.o')
                os.system('rm *_wrap.c')
                os.system('rm *.csv')
                os.system('rm *.txt')
                os.system('rm *.dat')
        finally:        
            os.chdir('..')


dagpype_c = Extension('dagpype_c',
    include_dirs = ['/usr/local/include'] + 
        numpy.distutils.misc_util.get_numpy_include_dirs(),
    language = 'c++',
    depends = [
        'dagpype/line_writer.hpp',
        'dagpype/correlator.hpp',
        'dagpype/enumerator.hpp',
        'dagpype/dbg.hpp',
        'dagpype/col_reader.hpp', 
        'dagpype/array_col_reader.hpp', 
        'dagpype/_line_to_array.hpp', 
        'dagpype/defs.hpp',
        'dagpype/parser_defs.hpp',
        'dagpype/line_to_tuple.hpp',
        'dagpype/exp_averager.hpp'],
    sources = [
        'dagpype/line_writer.cpp',
        'dagpype/correlator.cpp',
        'dagpype/enumerator.cpp',
        'dagpype/col_reader.cpp', 
        'dagpype/array_col_reader.cpp', 
        'dagpype/_line_to_array.cpp', 
        'dagpype/module.cpp', 
        'dagpype/defs.cpp',
        'dagpype/parser_defs.cpp',
        'dagpype/line_to_tuple.cpp',
        'dagpype/exp_averager.cpp'])


setup(
    name = 'DAGPype',
    version = '0.1.5.1',
    author = 'Ami Tavory',
    author_email = 'atavory at gmail.com',
    packages = ['dagpype', 'dagpype.np', 'dagpype.plot'],
    url = 'http://pypi.python.org/pypi/DAGPype',
    license = 'BSD',
    description = 'Low-footprint flexible data-processing and data-preparation pipelines',
    long_description = open('README.txt').read(),
    requires = ['numpy', 'matplotlib', 'unittest_rand_gen_state'],
    ext_modules = [dagpype_c],
    cmdclass = { 
        'test': _TestCommand, 
        'performance_test': _PerformanceTestCommand,
        'document': _DocumentCommand},
    classifiers = [
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',   
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: C++',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Information Analysis',
        'Topic :: Software Development :: Libraries :: Python Modules'])





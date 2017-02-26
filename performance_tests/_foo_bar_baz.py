import os
import sys
import math
import csv
import time

import _src
sys.path.extend(['..', '../..'])
from dagpype import *


_f_name = 'perf.txt'


def _chunking_pipe():
    np.chunk_source(open(_f_name)) | \
        filt(lambda ls: ''.join(l.replace('foo', 'bar') if 'baz' in l else l for l in ls)) | \
        to_stream('chunking_pipe_bar.txt')


def _pipe():
    stream_lines(_f_name, rstrip = False) | \
        filt(lambda l: l.replace('foo', 'bar') if 'baz' in l else l) | \
        to_stream('pipe_bar.txt', line_terminator = b'')
            
            
def _sed():
    os.system("sed '/baz/s/foo/bar/g' %s > sed_bar.txt" % _f_name)
    
    
def _std():
    i = open(_f_name, 'r')
    o = open('std_bar.txt', 'w')
    for l in i:
        o.write((l.replace('foo', 'bar') if 'baz' in l else l))    


def _awk():
    os.system("awk '/baz/ { gsub(/foo/, \"bar\") }; { print }' %s > awk_bar.txt" % _f_name)


def _perl():
    os.system("perl -pe '/baz/ && s/foo/bar/' %s > perl_bar.txt" % _f_name)


def _run_test(fn, num_lines, num_chars, num_its):
    _src.make_text_file(_f_name, num_lines, num_chars)
    start = time.time()
    for i in range(num_its):
        fn()
    end = time.time()
    diff = (end - start) / num_its
    os.remove(_f_name)
    return diff


def run_tests(names, num_lines, num_chars, num_its):
    fns = dict([
        ('chunking dagpype', lambda : _chunking_pipe()),
        ('dagpype', lambda: _pipe()),
        ('awk', lambda : _awk()),
        ('sed', lambda: _sed()),
        ('perl', lambda : _perl()),
        ('standard Python', lambda: _std())])
    t = dict([])        
    for name in names:        
        t[name] = _run_test(fns[name], num_lines, num_chars, num_its)
    return t



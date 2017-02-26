import random
import string
import os
import numpy
import sys
    
    
def make_text_file(f_name, num_lines, num_chars):
    def _rand_line():
        len_ = int(random.expovariate(1. / num_chars))
        return ''.join(random.choice(string.ascii_letters) for x in range(len_)) + '\n'
        
    if os.path.exists(f_name):
        os.remove(f_name)
    with open(f_name, 'wb') as f:
        for i in range(num_lines):
            f.write(_rand_line())
            
            
def make_header_csv_file(f_name, num_rows, num_cols):
    if os.path.exists(f_name):
        os.remove(f_name)
    with open(f_name, 'wb') as f:
        f.write(','.join([str(i) for i in range(num_cols)]) + '\n')
        for i in range(num_rows):
            f.write(','.join([str(random.random()) for i in range(num_cols)]) + '\n')


def make_csv_file(f_name, num_rows, num_cols):
    if os.path.exists(f_name):
        os.remove(f_name)
    with open(f_name, 'wb') as f:
        for i in range(num_rows):
            f.write(','.join([str(random.random()) for i in range(num_cols)]) + '\n')


def make_tsv_file(f_name, num_rows, num_cols):
    if os.path.exists(f_name):
        os.remove(f_name)
    with open(f_name, 'wb') as f:
        for i in range(num_rows):
            f.write('\t'.join([str(random.random()) for i in range(num_cols)]) + '\n')


def make_binary_file(f_name, num_elems):
    with open(f_name, 'wb') as writer:
        writer.write(numpy.random.rand(num_elems).tostring())




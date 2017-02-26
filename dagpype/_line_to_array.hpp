#ifndef _LINE_TO_ARRAY_HPP
#define _LINE_TO_ARRAY_HPP

#include <Python.h>

#include "parser_defs.hpp"

long
_line_to_array(
    const long * cols, const long * unique_cols, 
    long num_cols, long max_col,
    char delimit, char comment, int skip_init_space,
    const char * c, long len, _ParsedT parsed[max_num_cols]);
long
_line_to_array(
    const long * cols, const long * unique_cols, 
    long num_cols, long max_col,
    char delimit, int skip_init_space,
    const char * c, long len, _ParsedT parsed[max_num_cols]);

#endif // #ifndef _LINE_TO_ARRAY_HPP




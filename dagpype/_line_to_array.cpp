#include <Python.h>
#include <structmember.h>

#include "_line_to_array.hpp"

using namespace std;

static inline bool 
_should_parse(const long * unique_cols, long unique_col_i, long col_i)
{
    return (unique_cols == NULL || unique_cols[unique_col_i] == col_i);
}

static bool 
add_field(
    bool should_parse,
    const char * c,
    long len,
    _ParsedT parsed[max_num_cols],
    long & col_i)
{
    if (!should_parse)
        return true;

    if (col_i == max_num_cols) {
        PyErr_Format(PyExc_IndexError, "Max num cols exceeded");
        return false;
    }

    parsed[col_i++] = make_pair(c - len, c);
    return true;
}
    
long
_line_to_array(
    const long * cols, const long * unique_cols, 
    long num_cols, long max_col,
    char delimit, char comment, int skip_init_space,
    const char * c, long len, 
    _ParsedT parsed[max_num_cols])
{
    DBG_VERIFY(len >= 0);
    long unique_col_i = 0, col_i = 0, in_col_i = 0;
    bool should_parse = _should_parse(unique_cols, 0, 0);
    while (len--) {
        if (*c == delimit){
            if (!add_field(should_parse, c, in_col_i, parsed, unique_col_i))
                return -1;
            ++col_i;
            if(cols != NULL && col_i > max_col)
                break;
            should_parse = _should_parse(unique_cols, unique_col_i, col_i);
            in_col_i = 0;
            ++c; 
            continue;
        }

        if (*c == comment || *c == '\n' || *c == '\r'){
            break;
        }

        if (!should_parse) {
            ++c;
            continue;
        }
    
        if (*c == ' ' && in_col_i == 0 && skip_init_space) {
            ++c; 
            continue;
        }

        ++in_col_i;
        if (in_col_i == max_field_len) {
            PyErr_Format(PyExc_IndexError, "Max col length exceeded");
            return -1;
        }

        ++c; 
    }
    
    if (!add_field(should_parse, c, in_col_i, parsed, unique_col_i))
        return -1;

    return unique_col_i;
}

long
_line_to_array(
    const long * cols, const long * unique_cols, 
    long num_cols, long max_col,
    char delimit, int skip_init_space,
    const char * c, long len, 
    _ParsedT parsed[max_num_cols])
{
    DBG_VERIFY(len >= 0);
    long unique_col_i = 0, col_i = 0, in_col_i = 0;
    bool should_parse = _should_parse(unique_cols, 0, 0);
    while (len--) {
        if (*c == delimit){
            if (!add_field(should_parse, c, in_col_i, parsed, unique_col_i))
                return -1;
            ++col_i;
            if(cols != NULL && col_i > max_col)
                break;
            should_parse = _should_parse(unique_cols, unique_col_i, col_i);
            in_col_i = 0;
            ++c; 
            continue;
        }

        if (*c == '\n' || *c == '\r'){
            break;
        }

        if (!should_parse) {
            ++c;
            continue;
        }
    
        if (*c == ' ' && in_col_i == 0 && skip_init_space) {
            ++c; 
            continue;
        }

        ++in_col_i;
        if (in_col_i == max_field_len) {
            PyErr_Format(PyExc_IndexError, "Max col length exceeded");
            return -1;
        }

        ++c; 
    }
    
    if (!add_field(should_parse, c, in_col_i, parsed, unique_col_i))
        return -1;

    return unique_col_i;
}


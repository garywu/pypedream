#ifndef PARSER_DEFS_HPP
#define PARSER_DEFS_HPP

#include <utility>
#include <vector>

#include "defs.hpp"

#if defined(__CYGWIN__) || defined(__CYGWIN32__)
#define DAGPYPE_NO_USE_AIO
#endif // #if defined(__CYGWIN__) || defined(__CYGWIN32__)

#if defined(__MINGW32__) || defined(__MINGW64__)
#define DAGPYPE_NO_USE_AIO
#endif // #if defined(__MINGW32__) || defined(__MINGW64__)

#if defined(_WIN32) || defined (_WIN64)
#define DAGPYPE_NO_USE_AIO
#endif // #if defined(_WIN32) || defined (_WIN64)

#if defined(__APPLE__)
#define DAGPYPE_NO_USE_AIO
#endif // #if defined(__APPLE__)

#if defined(__GNUC__) && !defined(DAGPYPE_NO_USE_AIO)
#define DAGPYPE_USE_AIO
#endif // #if defined(__GNUC__) && !defined(DAGPYPE_NO_USE_AIO)

void 
_parse_comment(PyObject * comment_obj, bool & has_comment, char & comment);

typedef std::vector<char> buf_t;

enum{_int = 0, _float = 1, _str = 2};
enum{_inds_cols = 0, _names_cols = 1, _all_cols = 2};
enum{max_num_cols = 1000, max_field_len = 128};

typedef std::pair<const char *, const char *> _ParsedT;

PyObject * 
_ParsedTo_string(const _ParsedT & t);

long
_ParsedTo_long(const _ParsedT & t, bool & err);
PyObject * 
_ParsedTo_int(const _ParsedT & t);

double
_ParsedTo_double(const _ParsedT & t, bool & err);
PyObject * 
_ParsedTo_float(const _ParsedT & t);

char * 
pystring_as_string(PyObject * o, long & len);

long *
parse_longs(PyObject * iterator, long & num, bool & err);
char * *
parse_strings(PyObject * iterator, long & num, bool & err);

extern "C" PyObject *
parser_max_field_len(PyObject *module, PyObject *args, PyObject *keyword_args);

#endif // #ifndef PARSER_DEFS_HPP

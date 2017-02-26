#ifndef LINE_WRITER_HPP
#define LINE_WRITER_HPP

#include "parser_defs.hpp"

extern "C" PyObject *
line_writer(PyObject *module, PyObject *args, PyObject *keyword_args);
extern "C" PyObject *
line_writer_write(PyObject *module, PyObject *args, PyObject *keyword_args);
extern "C" PyObject *
line_writer_close(PyObject *module, PyObject *args, PyObject *keyword_args);

extern PyTypeObject LineWriterType;

#endif // #ifndef LINE_WRITER_HPP




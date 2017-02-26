#include <Python.h>
#include <structmember.h>
#include <numpy/arrayobject.h>

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

#include "defs.hpp"
#include "line_writer.hpp"

#ifdef DAGPYPE_USE_AIO
#include <sys/types.h>
#include <sys/uio.h>
#include <sys/unistd.h>
#include <stdio.h>
#endif // #ifdef DAGPYPE_USE_AIO

using namespace std;

struct LineWriter
{
    PyObject_HEAD
    
    string * line_terminator;      

    int fileno;    
#ifdef DAGPYPE_USE_AIO
    vector<iovec> * iovecs;
#endif // #ifdef DAGPYPE_USE_AIO
    
    bool first;
    
    long n;
};

extern PyTypeObject LineWriterType;

extern "C" int
line_writer_traverse(LineWriter * self, visitproc visit, void *arg)
{
    return 0;
}

extern "C" void
line_writer_dealloc(LineWriter * self)
{
    delete self->line_terminator;
#ifdef DAGPYPE_USE_AIO
    delete self->iovecs;
#endif // #ifdef DAGPYPE_USE_AIO

    PyObject_GC_UnTrack(self);

    PyObject_GC_Del(self);
}

extern "C" PyObject *
line_writer(PyObject *module, PyObject *args, PyObject *keyword_args)
{
#ifndef DAGPYPE_USE_AIO
    Py_RETURN_NONE;
#endif // #ifndef DAGPYPE_USE_AIO

    LineWriter * const self = PyObject_GC_New(LineWriter, &LineWriterType);
    if (self == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    
    self->line_terminator = NULL;
    self->fileno = -1;
#ifdef DAGPYPE_USE_AIO
    self->iovecs = NULL;
#endif // #ifdef DAGPYPE_USE_AIO
    self->first = true;

    char * line_terminator;
    if (!PyArg_ParseTuple(
            args,
            "is*",
            &self->fileno,
            &line_terminator) || self->fileno <= 0) {
        WARN("Failed to parse stuff " << self->fileno << " " << line_terminator);
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        Py_DECREF(self);
        return NULL;
    }

    try {
        self->line_terminator = new string(line_terminator);
#ifdef DAGPYPE_USE_AIO
        self->iovecs = new vector<iovec>();
#endif // #ifdef DAGPYPE_USE_AIO
    }
    catch(...) {
        PyErr_NoMemory();
        return NULL;
    }
    self->n = 0;
    
#ifdef DAGPYPE_USE_AIO
    fsync(self->fileno);    
    fdatasync(self->fileno);
#endif // #ifdef DAGPYPE_USE_AIO

    PyObject_GC_Track(self);
    return (PyObject *)self;
}

extern "C" int
line_writer_clear(LineWriter * self)
{
    return 0;
}

#ifdef DAGPYPE_USE_AIO
static iovec
make_iovec(const char * p, size_t len)
{
    iovec v;
    v.iov_base = const_cast<char *>(p);
    v.iov_len = len;
    return v;
}
#endif // #ifdef DAGPYPE_USE_AIO

#ifdef DAGPYPE_USE_AIO
static void
make_iovecs(LineWriter * self, PyObject * tup)
{
    self->n += PySequence_Length(tup);
    try {
        self->iovecs->reserve(2 * PySequence_Length(tup) + 2);    
    }
    catch(...) {
        PyErr_NoMemory();
        throw;
    }
    self->iovecs->resize(0);
    
    if (!self->first && !self->line_terminator->empty())    
        self->iovecs->push_back(make_iovec(
            &(*self->line_terminator)[0], 
            distance(self->line_terminator->begin(), self->line_terminator->end())));
    for (Py_ssize_t i = 0; i < PySequence_Length(tup); ++i) {
        PyObject * const p = PySequence_ITEM(tup, i);
        Py_ssize_t length;
        long len_;
        char * const buf = pystring_as_string(p, len_);
        length = static_cast<Py_ssize_t>(len_);
        self->iovecs->push_back(make_iovec(buf, length));
        Py_XDECREF(p);
        if (i + 1 < PySequence_Length(tup) &&  !self->line_terminator->empty())
            self->iovecs->push_back(make_iovec(
                &(*self->line_terminator)[0], 
                distance(self->line_terminator->begin(), self->line_terminator->end())));
    }
}
#endif // #ifdef DAGPYPE_USE_AIO

#ifdef DAGPYPE_USE_AIO
static void 
write_iovecs(LineWriter * self)
{    
    if (self->iovecs->empty())
        return;

    const int written = writev(self->fileno, &(*self->iovecs)[0], self->iovecs->size());
    if (written < 0) {
       PyErr_SetString(PyExc_IOError, "Failed to write");
       throw runtime_error("Failed to write");
    }
}
#endif // #ifdef DAGPYPE_USE_AIO

extern "C" PyObject *
line_writer_write(PyObject * module, PyObject * args, PyObject * keyword_args)
{        
    LineWriter * self;
    PyObject * tup;
    if (!PyArg_ParseTuple(
            args,
            "OO",
            reinterpret_cast<LineWriter * *>(&self), 
            &tup) || self == NULL || tup == NULL || !PySequence_Check(tup)) {
        WARN("Failed to parse stuff");
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }
    
    try {
#ifdef DAGPYPE_USE_AIO
        make_iovecs(self, tup);
        write_iovecs(self);
#endif // #ifdef DAGPYPE_USE_AIO
    }
    catch(...) {
        return NULL;
    }    
            
    self->first = false;

    Py_RETURN_NONE;
}

extern "C" PyObject *
line_writer_close(PyObject *module, PyObject *args, PyObject *keyword_args)
{
    LineWriter * self;
    if (!PyArg_ParseTuple(
            args,
            "O",
            reinterpret_cast<LineWriter * * >(&self)) || self == NULL) {
        WARN("Failed to parse stuff " << self);
        PyErr_SetString(PyExc_TypeError, "Failed to parse stuff");
        return NULL;
    }

    return pyint_from_long(self->n);
}

static PyMethodDef line_writer_methods[] = {
    { NULL}
};

static PyMemberDef line_writer_memberlist[] = {
    { NULL }
};

PyDoc_STRVAR(LineWriterType_doc, "");

PyTypeObject LineWriterType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "dagpype_c.line_writer",               /*tp_name*/
    sizeof(LineWriter),                   /*tp_basicsize*/
    0,                                      /*tp_itemsize*/
    /* methods */
    (destructor)line_writer_dealloc,          /*tp_dealloc*/
    0,                           /*tp_print*/
    0,                         /*tp_getattr*/
    0,                         /*tp_setattr*/
    0,                             /*tp_compare*/
    0,                            /*tp_repr*/
    0,                                      /*tp_as_number*/
    0,                                      /*tp_as_sequence*/
    0,                                      /*tp_as_mapping*/
    0,                            /*tp_hash*/
    0,                         /*tp_call*/
    0,                            /*tp_str*/
    0,                                      /*tp_getattro*/
    0,                                      /*tp_setattro*/
    0,                                      /*tp_as_buffer*/
    Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE | 
    Py_TPFLAGS_HAVE_GC,                     /*tp_flags*/
    LineWriterType_doc,                     /*tp_doc*/
    (traverseproc)line_writer_traverse,       /*tp_traverse*/
    (inquiry)line_writer_clear,               /*tp_clear*/
    0,                                      /*tp_richcompare*/
    0,                                      /*tp_weaklistoffset*/
    0,                      /*tp_iter*/
    0,                              /*tp_iternext*/
    line_writer_methods,                      /*tp_methods*/
    line_writer_memberlist,                   /*tp_members*/
    0,                                      /*tp_getset*/
};



/* corr.i */
%module c_corr
%{
    double c_corr(const char f_name[]);
    double c_corr_trunc(const char f_name[]);
    double c_corr_prune(const char f_name[]);
%}

extern double c_corr(const char f_name[]);
extern double c_corr_trunc(const char f_name[]);
extern double c_corr_prune(const char f_name[]);


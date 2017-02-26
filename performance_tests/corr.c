#include <stdio.h>
#include <math.h>
#include <assert.h>
#include <stdlib.h>


double c_corr_prune(const char f_name[])
{
    FILE *const pf = fopen(f_name, "rb");
    assert(pf != NULL);
    double sx = 0, sxx = 0, sy = 0, syy = 0, sxy = 0;
    size_t n = 0;
    while(1)
    {
        double x, y;
        if(fread(&x, sizeof(double), 1, pf) != 1 || fread(&y, sizeof(double), 1, pf) != 1 || feof(pf))
        {
            fclose(pf);
            break;
        }
        if(x >= 0.25 || y >= 0.25)
            continue;
        sx += x;
        sxx += x * x;
        sy += y;
        sxy += x * y;
        syy += y * y;
        ++n;
    }

    // printf("C %ld values\n", n);

    return (n * sxy - sx * sy) / sqrt(n * sxx - sx * sx) / sqrt(n * syy - sy * sy);
}


double c_corr_trunc(const char f_name[])
{
    FILE *const pf = fopen(f_name, "rb");
    assert(pf != NULL);
    double sx = 0, sxx = 0, sy = 0, syy = 0, sxy = 0;
    size_t n = 0;
    while(1)
    {
        double x, y;
        if(fread(&x, sizeof(double), 1, pf) != 1 || fread(&y, sizeof(double), 1, pf) != 1 || feof(pf))
        {
            fclose(pf);
            break;
        }
        x = fmin(x, 0.25);
        y = fmin(x, 0.25);
        sx += x;
        sxx += x * x;
        sy += y;
        sxy += x * y;
        syy += y * y;
        ++n;
    }

    // printf("C %ld values\n", n);

    return (n * sxy - sx * sy) / sqrt(n * sxx - sx * sx) / sqrt(n * syy - sy * sy);
}


double c_corr(const char f_name[])
{
    FILE *const pf = fopen(f_name, "rb");
    assert(pf != NULL);
    double sx = 0, sxx = 0, sy = 0, syy = 0, sxy = 0;
    size_t n = 0;
    while(1)
    {
        double x, y;
        if(fread(&x, sizeof(double), 1, pf) != 1 || fread(&y, sizeof(double), 1, pf) != 1 || feof(pf))
        {
            fclose(pf);
            break;
        }
        sx += x;
        sxx += x * x;
        sy += y;
        sxy += x * y;
        syy += y * y;
        ++n;
    }

    // printf("C %ld values\n", n);

    return (n * sxy - sx * sy) / sqrt(n * sxx - sx * sx) / sqrt(n * syy - sy * sy);
}


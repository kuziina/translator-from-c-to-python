// Тест 3: объявление переменных всех поддерживаемых типов:
// int, char, float, double, short, long, unsigned int, unsigned char,
// signed int, const, множественное объявление, объявление без инициализации
#include <stdio.h>

int main() {
    int a = 1;
    char c = 'z';
    float f = 1.5;
    double d = 2.5;
    short s = 10;
    long l = 100000;
    unsigned int u = 4000000000;
    unsigned char uc = 255;
    signed int si = -5;
    const int limit = 100;
    int x, y, z;
    x = 3;
    y = 4;
    z = x + y;
    printf("%d %c %f %f\n", a, c, f, d);
    printf("%d %d %d %d\n", s, l, uc, si);
    printf("%d %d %d\n", x, y, z);
    printf("%d\n", limit);
    return 0;
}

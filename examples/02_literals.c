// Тест 2: литералы всех видов (десятичные, hex, дробные, символьные,
// строковые с escape-последовательностями, true/false)
#include <stdio.h>

int main() {
    int dec = 42;
    int hex = 0x1F;
    int zero = 0;
    int neg = -7;
    float f = 3.14;
    double d = 2.71828;
    char letter = 'A';
    char newline = '\n';
    char tab = '\t';
    int yes = true;
    int no = false;
    printf("%d %d %d %d\n", dec, hex, zero, neg);
    printf("%f %f\n", f, d);
    printf("%c %c %c %d %d\n", letter, newline, tab, yes, no);
    printf("Строка с \"кавычками\" и табом:\tготово\n");
    printf("Процент: 50%%\n");
    return 0;
}

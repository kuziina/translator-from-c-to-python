// Тест 7: циклы — while, do-while, for, break, continue, вложенные циклы
#include <stdio.h>

int main() {
    // while
    int i = 0;
    while (i < 3) {
        printf("while %d\n", i);
        i++;
    }

    // do-while
    int j = 10;
    do {
        printf("do-while выполнится минимум раз: %d\n", j);
        j++;
    } while (j < 12);

    // for с составным присваиванием и декрементом
    int k;
    for (k = 5; k > 0; k--) {
        printf("for %d\n", k);
    }

    // break и continue внутри while
    int m = 0;
    while (m < 10) {
        m++;
        if (m % 2 == 0) {
            continue;
        }
        if (m > 6) {
            break;
        }
        printf("нечётное: %d\n", m);
    }

    // break внутри for
    int n;
    for (n = 0; n < 100; n++) {
        if (n == 3) {
            break;
        }
    }
    printf("остановились на %d\n", n);

    // вложенные циклы
    int a;
    int b;
    int total = 0;
    for (a = 1; a <= 3; a++) {
        for (b = 1; b <= 3; b++) {
            total = total + a * b;
        }
    }
    printf("сумма произведений: %d\n", total);

    // do-while с break
    int p = 0;
    do {
        p++;
        if (p == 2) {
            break;
        }
    } while (p < 100);
    printf("do-while break: %d\n", p);

    return 0;
}

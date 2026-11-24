// Тест 12: интеграционный — все возможности транслятора в одной программе
// (препроцессор, все типы, операторы, циклы, switch, функции, рекурсия, I/O)
#include <stdio.h>
#define SIZE 5
#define TITLE "Integration"

int square(int n) {
    return n * n;
}

int sum_to(int n) {
    if (n <= 0) {
        return 0;
    }
    return n + sum_to(n - 1);
}

void print_header() {
    printf("=== %s ===\n", TITLE);
}

int main() {
    print_header();

    // переменные разных типов и const
    const int base = 10;
    int i;
    int total = 0;
    float ratio = 0.5;
    char sep = '|';
    unsigned int big = 3000000000;

    // цикл с вычислениями и switch
    for (i = 1; i <= SIZE; i++) {
        int sq = square(i);
        total += sq;
        switch (i) {
            case 1:
                printf("первый квадрат: %d\n", sq);
                break;
            case SIZE:
                printf("последний квадрат: %d\n", sq);
                break;
            default:
                printf("квадрат: %d\n", sq);
                break;
        }
    }
    printf("всего: %d\n", total);

    // while с тернарным оператором
    int n = 0;
    while (n < base) {
        int parity = n % 2 == 0 ? 0 : 1;
        if (parity == 1) {
            printf("нечётное: %d\n", n);
        }
        n++;
    }

    // do-while и побитовые операции
    int flags = 0;
    int bit = 0;
    do {
        flags = flags | (1 << bit);
        bit++;
    } while (bit < 4);
    printf("флаги: %d\n", flags);

    // рекурсивная функция
    printf("sum_to(%d) = %d\n", base, sum_to(base));

    // логические и составные операторы
    int check = (total > 50) && (big > 0) ? 1 : 0;
    total *= 2;
    total -= 5;
    printf("проверка: %d, итог: %d\n", check, total);

    printf("множитель: %f, символ: %c\n", ratio, sep);
    print_header();

    #ifdef TITLE
    printf("макрос TITLE доступен\n");
    #endif

    return 0;
}

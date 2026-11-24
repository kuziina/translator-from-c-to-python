// Тест 8: switch / case / default, fall-through, break в ветках
#include <stdio.h>

int main() {
    int day = 3;

    switch (day) {
        case 1:
            printf("Понедельник\n");
            break;
        case 2:
            printf("Вторник\n");
            break;
        case 3:
            printf("Среда\n");
            break;
        case 4:
        case 5:
            printf("Конец недели\n");
            break;
        default:
            printf("Другой день\n");
            break;
    }

    // fall-through без break (несколько case подряд выполняются)
    int x = 1;
    int acc = 0;
    switch (x) {
        case 1:
            acc = acc + 1;
        case 2:
            acc = acc + 2;
            break;
        case 3:
            acc = acc + 4;
            break;
    }
    printf("acc = %d\n", acc);

    // switch, где срабатывает default
    int y = 99;
    switch (y) {
        case 1:
            printf("один\n");
            break;
        default:
            printf("default сработал\n");
            break;
    }

    // switch внутри цикла
    int i;
    for (i = 0; i < 3; i++) {
        switch (i) {
            case 0:
                printf("ноль\n");
                break;
            case 1:
                printf("один\n");
                break;
            default:
                printf("много\n");
                break;
        }
    }

    return 0;
}

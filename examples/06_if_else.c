// Тест 6: условные операторы if / else / else-if, вложенные условия
#include <stdio.h>

int main() {
    int x = 7;

    if (x > 5) {
        printf("x больше 5\n");
    }

    if (x < 0) {
        printf("x отрицательный\n");
    } else {
        printf("x неотрицательный\n");
    }

    if (x == 0) {
        printf("ноль\n");
    } else if (x < 10) {
        printf("однозначное число\n");
    } else {
        printf("многое\n");
    }

    // вложенные if
    if (x > 0) {
        if (x % 2 == 0) {
            printf("положительное чётное\n");
        } else {
            printf("положительное нечётное\n");
        }
    }

    // if без фигурных скобок
    if (x > 100)
        printf("не напечатается\n");
    else
        printf("else без скобок\n");

    return 0;
}

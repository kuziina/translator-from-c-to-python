// Тест 9: функции — параметры, возвращаемое значение, void-функция,
// рекурсия, вызов функции в выражении, вложенные вызовы
#include <stdio.h>

int add(int x, int y) {
    return x + y;
}

int fact(int n) {
    if (n <= 1) {
        return 1;
    }
    return n * fact(n - 1);
}

int fib(int n) {
    if (n < 2) {
        return n;
    }
    return fib(n - 1) + fib(n - 2);
}

void print_line(int n) {
    int i;
    for (i = 0; i < n; i++) {
        printf("-");
    }
    printf("\n");
}

int max3(int a, int b, int c) {
    int m = a;
    if (b > m) {
        m = b;
    }
    if (c > m) {
        m = c;
    }
    return m;
}

double average(int a, int b) {
    return (a + b) / 2.0;
}

int main() {
    print_line(10);
    printf("add(2, 3) = %d\n", add(2, 3));
    printf("fact(6) = %d\n", fact(6));
    printf("fib(10) = %d\n", fib(10));
    printf("max3(4, 9, 7) = %d\n", max3(4, 9, 7));
    printf("average(3, 8) = %f\n", average(3, 8));

    // вызов функции в выражении и вложенные вызовы
    int s = add(add(1, 2), add(3, 4));
    printf("сумма = %d\n", s);

    // результат функции в условии
    if (add(1, 1) == 2) {
        printf("сложение работает\n");
    }

    print_line(10);
    return 0;
}

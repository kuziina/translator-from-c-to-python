// Тест 5: унарные операции и инкременты/декременты (префиксные и постфиксные)
#include <stdio.h>

int main() {
    int i = 0;
    i++;
    i++;
    printf("%d\n", i);
    ++i;
    printf("%d\n", i);
    i--;
    --i;
    printf("%d\n", i);

    // инкремент внутри выражения цикла
    int n = 3;
    int j = 0;
    while (n > 0) {
        j++;
        n--;
    }
    printf("%d\n", j);

    // унарные +, -, !
    int a = 5;
    int negA = -a;
    int posA = +a;
    int notA = !a;
    printf("%d %d %d\n", negA, posA, notA);

    // побитовое отрицание
    int bNot = ~a;
    printf("%d\n", bNot);

    // постфиксный/префиксный инкремент как условие цикла for
    int k = 0;
    int count = 0;
    for (k = 0; k < 5; k++) {
        count++;
    }
    for (k = 5; k > 0; --k) {
        count--;
    }
    printf("%d\n", count);
    return 0;
}

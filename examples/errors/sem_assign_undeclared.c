// EXPECT: E_SEM_UNDECLARED
// Тест: присваивание необъявленной переменной
#include <stdio.h>

int main() {
    int a = 1;
    total = a + 1;
    printf("%d\n", total);
    return 0;
}

// EXPECT: E_SEM_UNDECLARED
// Тест: использование необъявленной переменной
#include <stdio.h>

int main() {
    int a = 5;
    printf("%d\n", a + b);
    return 0;
}

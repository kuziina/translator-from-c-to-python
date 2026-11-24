// EXPECT: E_SEM_REDECLARED
// Тест: повторное объявление переменной в одной области видимости
#include <stdio.h>

int main() {
    int a = 1;
    int a = 2;
    printf("%d\n", a);
    return 0;
}

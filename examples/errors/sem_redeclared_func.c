// EXPECT: E_SEM_REDECLARED
// Тест: повторное объявление функции с тем же именем
#include <stdio.h>

int f(int x) {
    return x;
}

int f(int x) {
    return x + 1;
}

int main() {
    printf("%d\n", f(1));
    return 0;
}

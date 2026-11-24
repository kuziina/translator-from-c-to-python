// EXPECT: E_SEM_FUNC_UNDECLARED
// Тест: вызов необъявленной функции
#include <stdio.h>

int main() {
    int r = compute(5);
    printf("%d\n", r);
    return 0;
}

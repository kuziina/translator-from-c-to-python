// EXPECT: E_SEM_LVALUE
// Тест: присваивание не идентификатору (слева не lvalue)
#include <stdio.h>

int main() {
    int x = 5;
    5 = x;
    printf("%d\n", x);
    return 0;
}

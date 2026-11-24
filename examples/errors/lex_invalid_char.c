// EXPECT: E_LEX_INVALID_CHAR
// Тест: недопустимый символ в исходном коде
#include <stdio.h>

int main() {
    int a = 5;
    int b = a @ 3;
    printf("%d\n", b);
    return 0;
}

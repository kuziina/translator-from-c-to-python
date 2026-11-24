// EXPECT: E_LEX_INVALID_CHAR
// Тест: недопустимый символ $ вне строки
#include <stdio.h>

int main() {
    int money$ = 100;
    printf("%d\n", money$);
    return 0;
}

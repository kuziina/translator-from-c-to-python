// EXPECT: E_SEM_CONST_MODIFY
// Тест: изменение константы
#include <stdio.h>

int main() {
    const int limit = 10;
    limit = 20;
    printf("%d\n", limit);
    return 0;
}

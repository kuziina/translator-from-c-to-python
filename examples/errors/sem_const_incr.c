// EXPECT: E_SEM_CONST_MODIFY
// Тест: инкремент константы
#include <stdio.h>

int main() {
    const int num = 5;
    num++;
    printf("%d\n", num);
    return 0;
}

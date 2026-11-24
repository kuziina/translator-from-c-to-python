// EXPECT: E_SEM_ARGS_COUNT
// Тест: неверное количество аргументов при вызове функции
#include <stdio.h>

int add(int x, int y) {
    return x + y;
}

int main() {
    printf("%d\n", add(1, 2, 3));
    return 0;
}

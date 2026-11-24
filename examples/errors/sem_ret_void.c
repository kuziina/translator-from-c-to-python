// EXPECT: E_SEM_RET_VOID
// Тест: void-функция возвращает значение
#include <stdio.h>

void show(int x) {
    return x;
}

int main() {
    show(1);
    return 0;
}

// EXPECT: E_PARSE
// Тест: объявление функции без типа возвращаемого значения
#include <stdio.h>

foo() {
    printf("без типа\n");
}

int main() {
    foo();
    return 0;
}

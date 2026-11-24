// EXPECT: E_PARSE
// Тест: пропущена точка с запятой после объявления
#include <stdio.h>

int main() {
    int a = 5
    int b = 10;
    printf("%d\n", a + b);
    return 0;
}

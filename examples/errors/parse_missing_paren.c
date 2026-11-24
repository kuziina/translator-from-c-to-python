// EXPECT: E_PARSE
// Тест: не закрыта круглая скобка в условии if
#include <stdio.h>

int main() {
    int x = 5;
    if (x > 3 {
        printf("да\n");
    }
    return 0;
}

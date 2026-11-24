// EXPECT: E_SEM_LOOP_CTRL
// Тест: break вне цикла или switch
#include <stdio.h>

int main() {
    int a = 1;
    if (a == 1) {
        break;
    }
    printf("%d\n", a);
    return 0;
}

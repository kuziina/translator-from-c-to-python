// EXPECT: E_SEM_LOOP_CTRL
// Тест: continue вне цикла
#include <stdio.h>

int main() {
    int a = 1;
    if (a == 1) {
        continue;
    }
    printf("%d\n", a);
    return 0;
}

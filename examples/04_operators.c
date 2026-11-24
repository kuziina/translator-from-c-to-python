// Тест 4: операторы — арифметические, сравнения, логические, побитовые,
// сдвиги, составное присваивание, тернарный оператор
#include <stdio.h>

int main() {
    int a = 10;
    int b = 3;
    int sum = a + b;
    int dif = a - b;
    int mul = a * b;
    int div = a / b;
    int mod = a % b;
    int gt = a > b;
    int lt = a < b;
    int ge = a >= b;
    int le = a <= b;
    int eq = a == b;
    int neq = a != b;
    int lgAnd = a && b;
    int lgOr = a || b;
    int lgNot = !a;
    int bAnd = a & 6;
    int bOr = a | 1;
    int bXor = a ^ 3;
    int bNot = ~a;
    int shL = 1 << 4;
    int shR = 64 >> 2;
    printf("%d %d %d %d %d\n", sum, dif, mul, div, mod);
    printf("%d %d %d %d %d %d\n", gt, lt, ge, le, eq, neq);
    printf("%d %d %d\n", lgAnd, lgOr, lgNot);
    printf("%d %d %d %d\n", bAnd, bOr, bXor, bNot);
    printf("%d %d\n", shL, shR);

    // составное присваивание
    a += 5;
    a -= 2;
    a *= 3;
    a /= 4;
    a %= 5;
    printf("%d\n", a);

    // тернарный оператор
    int max = a > b ? a : b;
    int sign = a > 0 ? 1 : -1;
    printf("%d %d\n", max, sign);
    return 0;
}

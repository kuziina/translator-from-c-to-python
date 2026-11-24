// Тест 11: ввод-вывод — printf со всеми спецификаторами (%d, %i, %f, %s, %c, %%),
// с шириной и точностью; scanf (в трансляторе генерируется заглушка)
#include <stdio.h>

int main() {
    int age = 25;
    float height = 1.75;
    double pi = 3.14159;
    char grade = 'A';
    int a = 0;
    int b = 0;

    printf("Возраст: %d\n", age);
    printf("Возраст: %i\n", age);
    printf("Рост: %f\n", height);
    printf("Пи: %f\n", pi);
    printf("Оценка: %c\n", grade);
    printf("Имя: %s, возраст: %d\n", "Иван", age);
    printf("Проценты: 100%%\n");
    printf("%5.2f\n", pi);
    printf("%10d|\n", age);

    // scanf: транслятор не поддерживает — генерирует заглушку с комментарием
    printf("Введите два числа: ");
    scanf("%d %d", &a, &b);
    printf("Сумма: %d\n", a + b);

    return 0;
}

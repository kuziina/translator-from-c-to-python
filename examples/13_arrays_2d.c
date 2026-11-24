// Тест 13: массивы — объявление, инициализация, доступ и изменение
// (одномерные, двумерные, вложенные и плоские инициализаторы)
#include <stdio.h>
#define ROWS 2
#define COLS 3

int sum_row(int row[COLS], int cols) {
    int s = 0;
    int j;
    for (j = 0; j < cols; j++) {
        s += row[j];
    }
    return s;
}

int main() {
    int matrix[ROWS][COLS] = {{1, 2, 3}, {4, 5, 6}};
    int zeros[2][2];
    int flat[2][3] = {7, 8, 9, 10, 11, 12};
    int i;
    int j;
    int total = 0;

    for (i = 0; i < ROWS; i++) {
        for (j = 0; j < COLS; j++) {
            printf("%d ", matrix[i][j]);
            total += matrix[i][j];
        }
        printf("\n");
    }

    matrix[0][1] = matrix[1][2] + flat[0][0];
    zeros[1][0] = matrix[0][1];
    matrix[1][1]++;
    total += sum_row(matrix[0], COLS);

    printf("total = %d\n", total);
    printf("matrix[0][1] = %d\n", matrix[0][1]);
    printf("zeros[1][0] = %d\n", zeros[1][0]);
    return 0;
}

// Тест 10: препроцессор — #include, #define (литеральные макросы),
// #ifdef / #else / #endif и #ifndef / #endif внутри тела функции
#include <stdio.h>
#define MAX 100
#define NAME "Translator"
#define DEBUG

int main() {
    int limit = MAX;
    printf("%s: лимит %d\n", NAME, limit);

    // макрос в выражении
    int half = MAX / 2;
    printf("половина лимита: %d\n", half);

    #ifdef DEBUG
    printf("отладка включена\n");
    #else
    printf("отладка выключена\n");
    #endif

    #ifndef UNKNOWN_MACRO
    printf("UNKNOWN_MACRO не определен\n");
    #endif

    // вложенные #ifdef
    #ifdef DEBUG
    #ifdef NAME
    printf("DEBUG и NAME определены\n");
    #endif
    #endif

    return 0;
}

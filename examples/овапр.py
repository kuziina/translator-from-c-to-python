# Тест 12: интеграционный — все возможности транслятора в одной программе
# (препроцессор, все типы, операторы, циклы, switch, функции, рекурсия, I/O)

SIZE = 5
TITLE = "Integration"

def square(n):
    return n * n

def sum_to(n):
    if n <= 0:
        return 0
    return n + sum_to(n - 1)

def print_header():
    print(f"=== {TITLE} ===\n")

def main():
    print_header()
    # переменные разных типов и const
    base = 10
    # int i
    total = 0
    ratio = 0.5
    sep = '|'
    big = 3000000000
    # цикл с вычислениями и switch
    i = 1
    while i <= SIZE:
        sq = square(i)
        total += sq
        if i == 1:
            print(f"первый квадрат: {sq}\n")
        elif i == SIZE:
            print(f"последний квадрат: {sq}\n")
        else:
            print(f"квадрат: {sq}\n")
        i += 1
    print(f"всего: {total}\n")
    # while с тернарным оператором
    n = 0
    while n < base:
        parity = (0 if (n % 2) == 0 else 1)
        if parity == 1:
            print(f"нечётное: {n}\n")
        n += 1
    # do-while и побитовые операции
    flags = 0
    bit = 0
    while True:
        flags = flags | (1 << bit)
        bit += 1
        if not (bit < 4):
            break
    print(f"флаги: {flags}\n")
    # рекурсивная функция
    print(f"sum_to({base}) = {sum_to(base)}\n")
    # логические и составные операторы
    check = (1 if (total > 50) and (big > 0) else 0)
    total *= 2
    total -= 5
    print(f"проверка: {check}, итог: {total}\n")
    print(f"множитель: {ratio}, символ: {sep}\n")
    print_header()
    print(f"макрос TITLE доступен\n")
    return 0

if __name__ == "__main__":
    main()


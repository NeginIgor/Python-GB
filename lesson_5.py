#Задача 26:  Напишите программу, которая на вход принимает два числа A и B, и возводит число А в целую степень B с помощью рекурсии.

def power(a, b):
    if b == 0: #если степень равна нулю, то результат равен 1
        return 1
    elif b == 1: #если степень равна 1, то результат равен самому числу a
        return a
    else: #иначе используем рекурсию, чтобы получить результат
        return a * power(a, b-1)

a = int(input("Введите число A: "))
b = int(input("Введите целую степень B: "))

result = power(a, b)

print(a, "в степени", b, "равно", result)


#Дана строка(возможно, пустая),состоящая из букв A-Z:AAAABBBCCXYZDDDDEEEFFFAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBB 
# Нужно написать функциюRLE,которая на выходе даст строку вида:A4B3C2XYZD4E3F3A6B28И сгенерирует ошибку,
#  если на вход пришла невалидная строка. Пояснения: Если символ встречается 1 раз,он остается без изменений; 
# Если символ повторяется более 1 раза, к нему добавляется количество повторений


def RLE(string):
    if not string.isalpha():
        raise ValueError('Invalid input string')
        
    result = ""
    count = 1
    prev_char = ""
    for char in string:
        if char == prev_char:
            count += 1
        else:
            if prev_char:
                result += prev_char + str(count)
            count = 1
            prev_char = char
    result += prev_char + str(count)
    return result
# Пример использования
input_string = "AAAABBBCCXYZDDDDEEEFFFAAAAAABBBBBBBBBBBBBBBBBBBBBBBBBBBB"
print(RLE(input_string)) # A4B3C2XYZD4E3F3A6B28
# Обработка невалидного ввода
invalid_string = "A1B2C3?!"
try:
    print(RLE(invalid_string))
except ValueError as e:
    print(str(e)) # Invalid input string

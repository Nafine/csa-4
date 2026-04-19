; --- Инициализация переменных (VarDecl) ---
LOAD  0x0000        ; Загружаем адрес начала строки "hello"
STORE 0x0006        ; hello = 0x0000
LOAD  1             ; ACC = 1
STORE 0x0007        ; a = 1
LOAD  2             ; ACC = 2
STORE 0x0008        ; b = 2

; --- b = a + b ---
LOAD  0x0007        ; Загружаем 'a'
PUSH                ; Сохраняем 'a' в стек
LOAD  0x0008        ; Загружаем 'b'
STORE 0x0009        ; Сохраняем 'b' в $tmp
POP                 ; Выталкиваем 'a' обратно в ACC
ADD   0x0009        ; ACC = ACC + $tmp (т.е. a + b)
STORE 0x0008        ; b = ACC

; --- b = a - b ---
LOAD  0x0007        ; a
PUSH
LOAD  0x0008        ; b
STORE 0x0009
POP
SUB   0x0009        ; ACC = a - b
STORE 0x0008

; --- b = a * b ---
LOAD  0x0007
PUSH
LOAD  0x0008
STORE 0x0009
POP
MUL   0x0009
STORE 0x0008

; --- b = a / b ---
LOAD  0x0007
PUSH
LOAD  0x0008
STORE 0x0009
POP
DIV   0x0009
STORE 0x0008

; --- if (a > b) ---
LOAD  0x0007        ; Снова вычисляем (a > b) для флага
PUSH
LOAD  0x0008
STORE 0x0009
POP
CMP   0x0009        ; Сравниваем a с $tmp (b)
JG    L_TRUE_1      ; Если больше, прыгаем на загрузку '1'
LOAD  0             ; Иначе загружаем '0' (Ложь)
JMP   L_END_1
L_TRUE_1:
LOAD  1             ; Загружаем '1' (Истина)
L_END_1:
JZ    L_ELSE_IF     ; Если в ACC '0', прыгаем к следующей проверке

; Блок print(hello)
LOAD  0x0006        ; Загружаем значение переменной hello (0x1000)
STORE 0xF000        ; Выводим адрес в порт (согласно твоей логике для переменных)
JMP   L_IF_FINISH
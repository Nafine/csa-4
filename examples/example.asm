; --- Инициализация переменных (VarDecl) ---
LOAD  0x1000        ; Загружаем адрес начала строки "hello"
STORE 0x1006        ; hello = 0x1000
LOAD  1             ; ACC = 1
STORE 0x1007        ; a = 1
LOAD  2             ; ACC = 2
STORE 0x1008        ; b = 2

; --- b = a + b ---
LOAD  0x1007        ; Загружаем 'a'
PUSH                ; Сохраняем 'a' в стек
LOAD  0x1008        ; Загружаем 'b'
STORE 0x1009        ; Сохраняем 'b' в $tmp
POP                 ; Выталкиваем 'a' обратно в ACC
ADD   0x1009        ; ACC = ACC + $tmp (т.е. a + b)
STORE 0x1008        ; b = ACC

; --- b = a - b ---
LOAD  0x1007        ; a
PUSH
LOAD  0x1008        ; b
STORE 0x1009
POP
SUB   0x1009        ; ACC = a - b
STORE 0x1008

; --- b = a * b ---
LOAD  0x1007
PUSH
LOAD  0x1008
STORE 0x1009
POP
MUL   0x1009
STORE 0x1008

; --- b = a / b ---
LOAD  0x1007
PUSH
LOAD  0x1008
STORE 0x1009
POP
DIV   0x1009
STORE 0x1008

; --- if (a > b) ---
LOAD  0x1007        ; Снова вычисляем (a > b) для флага
PUSH
LOAD  0x1008
STORE 0x1009
POP
CMP   0x1009        ; Сравниваем a с $tmp (b)
JG    L_TRUE_1      ; Если больше, прыгаем на загрузку '1'
LOAD  0             ; Иначе загружаем '0' (Ложь)
JMP   L_END_1
L_TRUE_1:
LOAD  1             ; Загружаем '1' (Истина)
L_END_1:
JZ    L_ELSE_IF     ; Если в ACC '0', прыгаем к следующей проверке

; Блок print(hello)
LOAD  0x1006        ; Загружаем значение переменной hello (0x1000)
STORE 0xF000        ; Выводим адрес в порт (согласно твоей логике для переменных)
JMP   L_IF_FINISH

; --- else if (a < b) ---
L_ELSE_IF:
LOAD  0x1007        ; Опять логика сравнения...
PUSH
LOAD  0x1008
STORE 0x1009
POP
CMP   0x1009
JL    L_TRUE_2
LOAD  0
JMP   L_END_2
L_TRUE_2:
LOAD  1
L_END_2:
JZ    L_ELSE        ; Если ложь, уходим в финальный else

; Блок print("a < b") — посимвольно (как в твоем _emit_call)
LOAD  97            ; 'a'
STORE 0xF000
LOAD  32            ; ' '
STORE 0xF000
LOAD  60            ; '<'
STORE 0xF000
LOAD  32            ; ' '
STORE 0xF000
LOAD  98            ; 'b'
STORE 0xF000
JMP   L_IF_FINISH

; --- else ---
L_ELSE:
LOAD  101           ; 'e'
STORE 0xF000
LOAD  108           ; 'l'
STORE 0xF000
LOAD  115           ; 's'
STORE 0xF000
LOAD  101           ; 'e'
STORE 0xF000

L_IF_FINISH:
HALT
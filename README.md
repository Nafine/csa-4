# CSA Lab 4

---

- **Вариант**: `alg | acc | neum | mc | tick | binary | stream | mem | cstr | prob1 | pipeline`
  - `alg`: синтаксис языка должен напоминать java/javascript/lua. Должен поддерживать математические выражения:
    1. В тестах необходимо осуществить проверку AST.
  - `acc`: Система команд должна быть построена вокруг аккумулятора:
    1. Инструкции изменяют значение, хранимое в аккумуляторе.
    2. Ввод-вывод осуществляется через аккумулятор
  - `neum`: фон Неймановская архитектура.
  - `mc`: Команды реализованы с помощью микрокоманд
  - `tick`: Процессор необходимо моделировать с точностью до такта, процесс моделирования может быть приостановлен на любом такте.
  - `binary`: Бинарное представление машинного кода
  - `stream`: Вввод-вывод осуществляется как через поток токенов.
  - `mem`: memory-mapped (порты ввода-вывода отображаются в память и доступ к ним осуществляется штатными командами)
  - `cstr`: Null-terminated (C string)
  - `prob1`: Euler problem 4 [link](https://projecteuler.net/problem=4)
  - `pipeline`: конвейерная организация работы процессора.
    1. Количество стадий конвейера -- не менее 3.
    2. Необходимо показать влияние конвейера на производительность написанных программ.

## Язык программирования

---

### Форма Бэкуса-Наура

```ebnf
program ::= top_level*

top_level ::= func_decl | var_decl

func_decl ::= "def" ID "(" params? ")" type block

params ::= param ("," param)*
param ::= ID type

block ::= "{" stmt* "}"

stmt ::= var_decl 
    | assign_stmt
    | expr_stmt
    | branch_stmt
    | while_stmt
    | return_stmt

var_decl ::= "var" ID type ("=" expr)? ";"
    | ID ":=" expr ";"

assign_stmt ::= ID "=" expr ";"

branch_stmt ::= "if" "(" expr ")" block 
                ("else" "if" "(" expr ")" block)*
                ("else" block)?

while_stmt ::= "while" "(" expr ")" block

return_stmt ::= "return" expr? ";"
expr_stmt ::= expr ";"

expr ::= expr "||" expr 
    | expr "&&" expr
    | expr ("==" | "!=") expr
    | expr ("<" | ">" | "<=" | ">=") expr 
    | expr ("+" | "-") expr
    | expr ("*" | "/" | "%") expr
    | unary_expr

unary_expr ::= "!" expr 
    | "-" expr
    | postfix_expr

primary_expr ::= ID
    | INT_LIT
    | FLOAT_LIT
    | BOOL_LIT
    | STRING_LIT
    | "(" expr ")"
    | func_call
                 
func_call ::= ID "(" args? ")"
    | "print" "(" expr ")"
    | "read" "(" ")"

args ::= expr ("," expr)*

type ::= "int" | "float" | "bool" | "string" | "void"

INT_LIT ::= [0-9]+
FLOAT_LIT ::= [0-9]+\.[0.9]+
BOOL_LIT ::= "true" | "false"
STRING_LIT ::= \"[^"]*\"
ID ::= [a-zA-Z_][a-zA-Z0-9_]*
```

### Семантика

- Стратегия вычислений -- аппликативная (applicative order)
- Области видимости -- лексические (lexical scoping)
    - Глобальные переменные - объявленные вне тела функций - доступны в любом месте программы
    - Локальные переменные - объявленные внутри функции - доступны только внутри этой функции
    - Затенение (shadowing) - локальная переменная может затенять глобальную переменную с тем же именем
- Типизация -- статическая, явная. Типы: `int`, `float`, `bool`, `string`, `void`
- Литералы -- целые числа (67), числа с плавающей точкой (3.14), булевы значения (true, false), строки ("hello")
- Комментарии -- однострочные (// comment)
- Точки входа -- функция `main` без параметров и возвращаемым значением `void`
- Строки -- null-terminated (C string)
- Ввод-вывод -- через встроенные функции `print` и `read`

## Организация памяти

---
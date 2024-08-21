# Conditionals

----

## What is a conditional?

**Control Flow** statement: affects how the computer progresses through our code

--- 

## If Statements

```python
x = 7

if x == 7:
    print("x is 7")
```

Note:
This code prints "x is 7"

--- 

## If-Else Statements

```python
x = 10

if x == 9:
    print("x is 9")
else:
    print("x is not 9")
```

Note:
This code prints "x is not 9"

--- 

## If-Elif Statements

```python
x = 11

if x == 10:
    print("x is 10")
elif x == 11:
    print("x is 11")
```

Note:
This code prints "x is 11"

---

## If-Elif-Else Statements
```python
x = 13

if x == 10:
    print("x is 10")
elif x == 11:
    print("x is 11")
elif x == 12:
    print("x is 12")
elif x == 13:
    print("x is 13")
elif x == 14:
    print("x is 14")
else:
    print("x is not between 10 and 14")
```

Note:
This code prints "x is 13"

----

## Comparison Operators

* We use comparison statements to "ask a question"
  * `==` Equal to
  * `!=` Not equal to
  * `>` Greater than
  * `>=` Greater than or equal to
  * `<` Less than
  * `<=` Less than or equal to
  * `in` 

---

## Testing membership

* Membership: whether one value is contained in another
* For now... Substring membership

```python
if "room" in "bedroom":
    print("1")

if "kitchen" in "kit":
    print("2")

if "word" in "you can also test if a word is part of a whole sentence":
    print("3")
```

Note:
This code prints "1" then "3"

----

# An Aside: Casting

---

## Casting
* Changes one datatype to another type
  * `str` to `int` is most common
  * `float` to `int` discards decimal part
* Will throw `ValueError` if you ask for something impossible

```python
a = "12"  # a is a string
b = int(a)  # b is an int

x = "12.7"  # x is a string
y = float(x)  # y is a float with the value 12.7
z = int(y)  # z is an int with the value 12
```

# Math

----

## Math

Python can do math for us, and it's really easy to make that happen!

Math is typically done as part of an assignment statement. Remember that the *destination* variable
goes to the left of the equal sign.

----

## Basic Operations

The 4 basic operations exist exactly like you think they would. 

* `+`: Addition
* `-`: Subtraction
* `*`: Multiplication
* `/`: Division

---

## Basic Operations in Code
See the following code:

```python
x = 2 + 3
y = x * 2
z = y / 5
a = z - 1

print(a)
```

What would be printed?

Note:
Solution: This code prints `1.0`

1. 2 + 3 is 5
2. 5 * 2 is 10
3. 10 / 5 is 2
4. 2 - 1 is 1
5. `a` has a final value of 1, which is what is printed.

Note that this is **bad code**. Creating a new variable every line works, but it will lead to very hard-to-read
and hard-to-debug code as a result. 

---
## Reusing Variables
This code is equivalent to the code on the last slide, but uses only one variable.

```python
x = 2 + 3
x = x * 2
x = x / 5
x = x - 1

print(x)
```

What would be printed?

Note:
Solution: This code prints `1.0`, just like the previous slide

----

## Other Operations

In addition to the four basic operations, we have some others that sometimes make our lives easier:

* `**`: To the power of
  * Eg. `2 ** 3` is "two cubed", and would make 8
* `//`: Integer division
  * Divides, and throws away the fractional part (ie, rounds down)
* `%`: Modulo
  * Gives us the remainder when we divide (we'll come back to this later)

---

## Other Operations in Code
See the following code:

```python
num = 23 % 5
num = num ** 3
num = num // 5
print(num)
```

What would be printed?

Note:
Solution: This code prints `5`.

1. When we divide 23 by 5, we get a remainder of 3 (along with 4 wholes, but those are discarded). 
2. 3 to the power of 3 is 27.
3. When we divide 27 by 5, we get 5 wholes (and a remainder of 2, which is discarded) 
4. `num` has a final value of 5, which is what is printed.

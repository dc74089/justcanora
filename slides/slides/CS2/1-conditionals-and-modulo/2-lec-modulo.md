# The Modulo Operator

----

## A Little Game

We're learning a new operator, called modulo, which looks like this: `%`
(it has nothing to do with percentages, it just shares the symbol)

On the next slide, I'll show you modulo problems with solutions.

Your job is to figure out the rule.

---

<div style="margin-bottom: 24px">
<ul>
<li>12 % 2 = 0</li>
<li>13 % 2 = 1</li>
<li>14 % 2 = 0</li>
<li>15 % 2 = 1</li>
</ul>
</div>
<div>
<ul>
<li>21 % 5 = 1</li>
<li>22 % 5 = 2</li>
<li>23 % 5 = 3</li>
<li>24 % 5 = 4</li>
<li>25 % 5 = 0</li>
<li>26 % 5 = 1</li>
</ul>
</div>

---

## Modulo is just Remainder

`a % b` -> "what is the remainder when you divide `a/b`?"

----

# Modulo Tricks

---

## Checking Divisibility

```python
if x % 7 == 0:
    print("x is divisible by 7")
```

---

## Evenness/Oddness

```python
if x % 2 == 0:
    print("x is even")
else:
    print("x is odd")
```
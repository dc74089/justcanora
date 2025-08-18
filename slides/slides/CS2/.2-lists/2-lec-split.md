# `str.split()`

----

## The Problem

I have a string that contains multiple items, I want to turn it into a list.

---

## Casting

Let's try casting:
```python
x = "Apples Bananas Cookies Detergent"
y = list(x)

print(y)
```

This would give us:
```python
['A', 'p', 'p', 'l', 'e', 's', ' ', 'B', 'a', 'n', 'a', 'n', 'a', 's', ' ', 'C', 'o', 'o', 'k', 'i', 'e', 's', ' ', 'D', 'e', 't', 'e', 'r', 'g', 'e', 'n', 't']
```

Which is not exactly what I'm looking for.

---

## A Different Way

We have a different way to turn a string into a list:

```python
x = "Apples Bananas Cookies Detergent"
y = x.split()

print(y)
```

Which gives us:
```python
['Apples', 'Bananas', 'Cookies', 'Detergent']
```

----

## The `.split()` Function

* We can use `x.split()`, where x is any string
* `.split()` can take zero or one argument
  * If we don't provide an argument, it will split on every space
  * If we want to split on a different character, we can provide it

---

## Splitting on a Different Character

This code:
```python
x = "Alpha/Bravo/Charlie/Delta"
y = x.split("/")

print(y)
```

Gives us:
```python
['Alpha', 'Bravo', 'Charlie', 'Delta']
```
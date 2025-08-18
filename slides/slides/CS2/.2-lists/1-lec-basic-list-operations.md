# Lists

----

## List Basics
* One variable that stores multiple values
* Every element in a list has an index (indexes at 0)
* In Python, elements of a list do *not* need to be the same type

---

<div style="text-align: center; width: 100%">
    <img src="STATICPREFIX/cs2/2-lists/film.png" style="width: 100%">
</div>

Note:
It is helpful to think of a list as a filmstrip. Every frame in the film has an index
(the first is index 0, the second is index 1, etc). Every frame can fit one and only one item.

We can
* Create an empty filmstrip
* Read what's in one cell of the filmstrip
* Replace what's in one cell of a filmstrip
* Splice something into a filmstrip
* Splice something out of a filmstrip

----

# List Operations

---

### Creating a list
```python
my_list = []
my_filled_list = [1, 2, "buckle", "my", True]
```

---

### Reading one element from a list using its index
```python
l = [1, "two", "tree", "fish"]

val = l[2]
print(val)  # Prints "tree"

print(l[0])  # Prints 1
```

---

### Replacing an element in a list
```python
l = [1, 2, 9, 4, 5]

print(l)  # Prints [1, 2, 9, 4, 5]

l[2] = 3

print(l)  # Prints [1, 2, 3, 4, 5]
```

---

### Length of a list

```python
my_favorite_numbers = [1, 4, 7, 17, 19, 27]

x = len(my_favorite_numbers)

print(x)  # Prints 6
```

---

### Adding to the end of a list
```python
x = [1, 2, 3]

x.append(4)

print(x)
```

---

### Adding to a given position of a list

```python
months = ["January", "March", "April"]
months.insert(1, "February")

print(months)  # Prints ['January', 'February', 'March', 'April']
```

---

### Removing an element by its index

```python
classes = ["Public Speaking", "Fling", "Fling Again!", "CS 1", "Planning"]

x = classes.pop(2)

print(classes)  # Prints ['Public Speaking', 'Fling', 'CS 1', 'Planning']
print(x)  # Prints "Fling Again!"
```

---

### Removing an element by its index (again)

```python
classes = ["Public Speaking", "Fling", "Fling Again!", "CS 1", "Planning"]

classes.pop(2)

print(classes)  # Prints ['Public Speaking', 'Fling', 'CS 1', 'Planning']
```

----

### Reference
If `z` is a list
* `len(z)` returns the length of z
* `z.append(123)` adds the value `123` to the end of `z`
* `z.insert(3, False)` inserts the value `False` between the 3rd and 4th element of `z`
  * False *becomes index 3*
* `z.pop(2)` removes and returns the 3rd element of `z`

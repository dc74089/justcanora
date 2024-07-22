# Python Syntax

----

## What is Syntax?
Syntax is, at a simple level, the order of words and symbols in a language.

---

## Why is Syntax Important?
Syntax carries meaning! Note the differences between these two sentences:

> The ball the kicked! girl

> The girl kicked the ball!

Note:
Only one of these sentences makes sense. If you put words in a different order, you change (or lose)
the meaning of a sentence. 

When we're programming, if you use the wrong syntax, you will get an error.

---

## Why is Syntax Important?
Now try these:

> Can you throw me that rubber blue big ball?

> Can you throw me that big blue rubber ball?

Note:
Both of these sentences may be technically correct, but the first one probably feels "off" to you.
In English, we have (loose) rules about the order of adjectives in a sentence, and when they aren't followed, we notice.

You probably didn't specifically learn that adjectives are presented in a certain order, but you definitely picked it up
through practice and repetition.

In case you're curious, here's the order of adjectives in English:
1. Quantity or number
2. Quality or opinion
3. Size
4. Age
5. Shape
6. Color
7. Proper adjective (often nationality, other place of origin, or material)
8. Purpose or qualifier

---

## Notes on Syntax

* Computers are cruel and unforgiving. Your syntax must be nearly-perfect, or else the computer will become very confused and throw an error.
* The best way to learn syntax is by **reading and writing code** and **making meaning from error messages**

Note:
I'm not going to teach you the rules of Python syntax, at least for now (I don't want you falling asleep). 
As we're reading and writing code together during our first few weeks, see if you can notice any patterns. 
We'll get into the nitty-gritty together later. 

----

# Your First Program
> A "Hello, World!" program is generally a simple computer program which outputs to the screen a message similar to "Hello, World!" while ignoring any user input. A small piece of code in most general-purpose programming languages, this program is used to illustrate a language's basic syntax. -Wikipedia

---

## Hello World
Let's create a "Hello World" program together! 

1. Open PyCharm
2. Start a New Project
3. Type the following code:
```python
print("Hello World!")
```
4. Run your code using the "play" button (make sure "current file" is selected!)

----

# Variables

---

## Variables
Variables are containers that can hold data. 

We can *assign* a value to a variable, or we can *read* the value of a variable.

Variables are referred to by a name that we choose. We have some rules for naming them:

* Can only contain letters, numbers, and underscores (`_`)
* Must not start with a number
* Must not be a reserved word
  * `False, def, if, raise, None, del, import, return, True, elif, in, try, and, else, is, while, as, except, lambda, with, assert, finally, nonlocal, yield, break, for, not, class, form, or, continue, global, pass`

---

## Data Types
We can't talk about variables without talking about the types of data that they can hold.

Here's a few that we are going to start with:
* String (`str`): Some text... Words, sentences, etc
  * Ex. `"Hello, my name is Dominic!"`. Note the double quotes.
* Integer (`int`): A positive or negative number, without a decimal part
  * Ex. `13` or `-2`
* Floating Point Number (`float`): A positive or negative number, with a decimal part
  * Ex. `3.14` or `-99.9`
* Boolean (`bool`): A value that is either true or false
  * Our only two options are `True` and `False`. Note the capitals.

---

## Assignment Statements
To create a variable and assign it a value, use the structure below:

```python
x = 10
pi = 3.14
lake = "highland"
hot_outside = True
```

Note that the *variable* is on the left, and its *value* is on the right.

---

## Printing Variables
To print the value of a variable, use the structure below:

```python
print(x)
```
(assuming you already have a variable named `x`)

---

## Variables Exercise
Let's write some code together! Please open a new file in PyCharm and write code to do the following:

1. Create a variable called `age`. Set it equal to your age.
2. Create a variable called `name`. Set it equal to your name.
3. Create a variable called `grade`. Set it equal to your grade.
4. Print the value of `name`.
5. Print the value of `age`.
6. Print the value of `grade`.

Note:
Solution:
```python
age = 25
name = "Dominic"
grade = 20
print(name)
print(age)
print(grade)
```

----

# Questions?
# Lists in HTML

---

## But first... A reminder:
When you write HTML code, at least at the start of this course, you should write it inside your `<body>` tag. Here's an example:

```html
<html>
    <body>
      <p>Hello, World!</p>
    </body>
</html>
```

----

## Lists
When we're creating a document, presentation, poster, etc., we may want to show a list of items. 

In HTML there are two types of lists: **Ordered Lists** and **Unordered Lists**

---

## Ordered Lists
An **ordered list** has, well, an order. It looks like this:

1. First thing
2. Second thing
3. Third thing

You might use it for a list of steps in a recipe, a ranking in a leaderboard, or in any other case where items have a natural ordering.

---

## Ordered Lists
### The HTML
```html
<ol>
    <li>First thing</li>
    <li>Second thing</li>
    <li>Third thing</li>
</ol>
```
### Produces
1. First thing
2. Second thing
3. Third thing

---

## Unordered Lists
An **unordered list**, by contrast, *does not* have an order. It looks like this:

* First thing
* Second thing
* Third thing

You might use it for a list of ingredients for a recipe, a collection of points in a presentation, or in any other case where items are not in a specific order.

---

## Unrdered Lists
### The HTML
```html
<ul>
    <li>First thing</li>
    <li>Second thing</li>
    <li>Third thing</li>
</ul>
```
### Produces
* First thing
* Second thing
* Third thing

----

## To Recap:
`<ol>` starts an Ordered List
`<ul>` starts an Unordered List

In both types, `<li>` starts a List Item

----

## Your Turn
Before the end of class, create a simple webpage containing a how-to guide.

Your how-to guide can be for any topic you choose. It should contain both:
* Materials needed (at least 5 items in an unordered list)
* Steps (also at least 5 items in an ordered list)
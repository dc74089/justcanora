# The Head

----

Remember, the `body` is for parts of our website that we see

We are going to be starting to add a `head` to our sites from here on out.

---

## The Head
We can include some hidden information in the `head` of our site, including:

* **Title**: The text that goes on the top tab
* **Favicon**: The image that shows on the top tab
* **Whole-Page Styles**

----

## Title
```html
<html>
    <head>
        <title>Title Of My Page</title>
    </head>
    
    <body>
    ...
    </body>
</html>
```

----

## Favicon
```html
<html>
    <head>
        <link rel="icon" href="my_image_name.png">
    </head>

    <body>
    ...
    </body>
</html>
```

----

## Whole-Page Styles
```html
<html>
    <head>
        <style>
            selector {
                property: value;
            }
        </style>
    </head>

    <body>
    ...
    </body>
</html>
```

---

## Let's Talk About It

* When we are between the `<style>` tags, we switch languages to CSS
  * (Just like when we are inside a `style="..."` argument of a tag)
* We have a new part of CSS: a **selector**...

---

## Selectors
* When we are putting CSS *inline* (the way we've always done it so far), we don't need to specify *which thing* is being styled
* When we put CSS in the head, we do. 
* The simplest selector is just a type of tag, like `img`, `a`, or `body` (or any others)

---

## Classes
* We can also add a *class* to some tags, and style all members of that class the same. 
* In the head, we use `.classname` as the selector.
  * The period means we are referring to a class.
* Here's an example:

---


```html
<html>
    <head>
        <style>
            .fancy {
                color: cornflowerblue;
                font-family: cursive;
            }
        </style>
    </head>

    <body>
        <p class="fancy">Line One</p>
        <p>Line Two</p>
        <p class="fancy">Line Three</p>
    </body>
</html>
```
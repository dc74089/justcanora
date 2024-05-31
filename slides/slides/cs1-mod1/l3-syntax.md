---
marp: true
theme: gradient
footer: Dominic Canora
paginate: true
headingDivider: 2
---


# HTML Syntax <!-- _class: title -->

# What is Syntax?
Syntax is, at a simple level, the order of words and symbols in a language.

# Why is syntax important?
* Syntax carries meaning! Note the differences between these two sentences:

    > The ball the kicked! girl

    > The girl kicked the ball!

* Computers are cruel and unforgiving. Your syntax must be nearly-perfect, or else the computer will become very confused and throw an error.

# HTML Syntax
HTML is comprised of **tags** and text. A tag takes the following format:
```html
<tagname argument="value" otherargument="value">
    You can put things inside of tags! They go here!
</tagname>
```

### Parts of a Tag
* Tag Name
* Arguments
* Contents
* Closing Tag

# Putting Tags Together
Tags can go inside of each other. Take the following example:
```html
<html>
    <p>You can put some <i>super</i> awesome text here!</p>
</html>
```

This code produces the following sentence: 

> You can put some *super* awesome text here!

We'll learn more about the `<html>`, `<p>`, and `<i>` tags later.

*Notice that every tag has a matching closing tag!*

# Common Error: Crossing Closing Tags
Tags need to be closed in the correct order so they do not overlap.

### Incorrect:
```html
<p>Hi there <b><i>friend</b></i></p>
```

In this example, the opening `<i>` tag is **inside** the `<b>` tag, but the closing `</i>` tag is **outside** the `</b>` tag.

### Correct:
```html
<p>Hi there <b><i>friend</i></b></p>
```
In this example, the `<i>` tag is fully inside the `<b>` tag.

# Correct or Incorrect?
```html
<html>
    <body>
        <div>
            <table>
                ...
            </table>
        </div>
    </body>
</html>
```


# Correct or Incorrect?
```html
<html>
    <body>
        <p>
            Hello, World!
        </body>
    </p>
</html>
```

# Some Common Tags
* `<html>`: Should contain your entire webpage
* `<body>`: Should contain everything that your user will see
* `<h1>` through `<h6>`: Headings (smaller number = bigger text)
* `<p>`: Paragraph
* `<b>`: Bold
* `<i>`: Italic
* `<u>`: Underline

# Let's Review
Before you start work on your first programming assignment, please open VS Code and we'll review how to create files, and how to open an HTML file in Chrome.

# Try it out! <!-- _class: title -->
Please start working on the "HTML Hello World" assignment on Canvas
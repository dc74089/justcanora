# Web Browsers & HTML Syntax

----

# Web Browsers

---

## Role of a Simple Web Browser
* Request documents
    * Download HTML, CSS, and JavaScript files from a server
* Render HTML & CSS
    * Turn HTML and CSS code into text and images on the screen
* Execute JavaScript
    * Run JS code that may alter the looks or behavior of a page
* Handle Clicks
    * Navigate to a new page or run JS code if a user clicks on a link, button, or other interactive element

---

## Some Other Things Web Browsers Do:
* Keep track of history and cookies
* Allow the user to save bookmarks, passwords, addresses, credit cards, etc.
* Run extensions that modify how pages behave
* Allow webpages to access local resources (files, camera, microphone, etc.)

----

# HTML Syntax

---

## What is Syntax?
Syntax is, at a simple level, the order of words and symbols in a language.

---

## Why is syntax important?
* Syntax carries meaning! Note the differences between these two sentences:

    > The ball the kicked! girl

    > The girl kicked the ball!

* Computers are cruel and unforgiving. Your syntax must be nearly-perfect, or else the computer will become very confused and throw an error.

----

## HTML Syntax
The most basic piece of HTML is a *tag*. It looks like this:
```html
<tagname>
```

With a few exceptions, every tag needs a matching *closing tag*, like this:

```html
<tagname> </tagname>
```

Tags can have *arguments*. That looks like this:
```html
<tagname arg1="value1" foo="bar"> </tagname>
```

We can put text *or other tags* between the opening and closing tag, like this:

```html
<p>Hi there! I'm <i>really</i> excited to meet you!</p>
```

---

## Common Error: Crossing Closing Tags
Tags need to be closed in the correct order so they do not overlap.
 
#### Incorrect:
```html
<p>Hi there <b><i>friend</b></i></p>
```

#### Correct:
```html
<p>Hi there <b><i>friend</i></b></p>
```

---

## Correct or Incorrect?
```html
<html>
  <body>
    <div>
      <table>
        
      </table>
    </div>
  </body>
</html>
```

---

## Correct or Incorrect?
```html
<html>
  <body>
    <p>
      Hello, World!
    </body>
  </p>
</html>
```

----

## Some Common Tags
* `<html>`: Should contain your entire webpage
* `<body>`: Should contain everything that your user will see
* `<h1>` through `<h6>`: Headings (smaller number = bigger text)
* `<p>`: Paragraph
* `<b>`: Bold
* `<i>`: Italic
* `<u>`: Underline

----

## Let's Review
Before you start work on your first programming assignment, please open VS Code and we'll review how to create files, and how to open an HTML file in Chrome.

----

## Try it out!
Please start working on the "HTML Hello World" assignment on Canvas
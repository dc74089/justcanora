# Basic Styling

----

## The Problem

Right now, unless you've been working ahead, our websites are... Well, *ugly*.

We want to add some <span style="color: #00ff55;">color</span> and <span style="font-family: cursive;">formatting</span> to better control what our site looks like.

---

Said another way, we have the bones, now it's time for...

---

# The Skin

----

## CSS
It's time to add our second language to the mix!

We're going to be writing Cascading Style Scripts (CSS) to control how elements of our webpages look.

---

## CSS Syntax

CSS has *properties* and *values*. It looks like this:

```css
color: blue;
```

In this case, the *property* is color, and the *value* is blue.

---

## Adding CSS

CSS goes *inside opening tags*, using the `style` attribute... Like this:

```html
<p style="color: blue;">This text will be blue</p>
```

When we view our webpage, it will look like this:

<div style="margin-left: 64px">
<p style="color: blue;">This text will be blue</p>
</div>

----

## Common CSS Attributes
Below is a list of common CSS attributes:

* `height` and `width`: Controls how big an element is on the screen
  * We use either pixels (like `24px`) or percentages (like `50%`) as our units
  * Make sure your unit is touching your number!
* `text-align`: Control where (horizontally) child items are.
  * Options are `left`, `right`, and `center`
* `color`: Controls the color of text.
  * <span style="color: yellow;">Like This</span>
* `background-color`: Controls the background color of an element
  * <span style="background-color: darkgreen;">Like This</span>
* `font-family`: Sets the font of text inside an element
  * By default, here are your options: arial, verdana, tahoma, georgia, garamond, monospace, cursive
* `font-size`: Sets the size of text inside an element
  * Your unit for this is `pt`. Make sure your unit is touching your number!

&nbsp;

(you can also find these, with even more information, on our cheat sheet)


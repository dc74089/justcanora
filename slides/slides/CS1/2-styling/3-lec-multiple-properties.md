# Multiple CSS Properties

----

## Adding Multiple Styles

You can use multiple CSS properties inside the same `style` block. That looks like this:

```html
<p style="color: blue; background-color: yellow;">Sup</p>
```

When we view our webpage, it will look like this:

<div style="margin-left: 64px; margin-right: 64px">
<p style="color: blue; background-color: yellow;">Sup</p>
</div>

---

## Which is correct?

&nbsp;

### A:
```html
<h1 style="font-family: cursive" style="color: green">Hello, World!</h1>
```

### B:
```html
<h1 style="font-family: cursive; color: green">Hello, World!</h1>
```
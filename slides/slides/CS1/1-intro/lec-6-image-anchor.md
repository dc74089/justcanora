# Images & Anchors

----

## Images
Sometimes we want to show an image on our webpage. 

Thankfully, that's pretty easy! We do have a few steps to complete first:

1. Make sure the image is stored *locally* on our computer
2. Make sure the image is stored in the same directory as our HTML file
   * We can also store the image in a subfolder of the HTML file's folder, but that makes things a bit more complex, and we'll get there later.

---

## Images
### The HTML
```html
<img src="your-filename-here" />
```

Open up an `img` tag, pass in your image's filename under `src`, and that's it!

>You'll notice that the `img` tag does not have a closing tag, and ends with a `/>` instead of just a `>`. This is because the `img` tag is *self-closing*.
>
>It's best to write an `img` tag as shown above, but if you forget that last slash (ie, if you end with `>` instead of `/>`), most browsers will tolerate it.

----

## Anchors
Sometimes, we want to link our webpage to another page on our site, or a different site altogether. Thankfully, this is also very easy!

* If we're linking to a different HTML file that we wrote, the two files need to be in the same directory.
    * Again, we *could* have the second file in a subfolder but it'll make our life more complicated.
* If we're linking to a different website, we need to know its URL.

---

## Anchors
### The HTML
```html
<a href="your-url-or-filename-here">Text of the link</a>
```

Open up an `a` tag, give the `href` (location the link will navigate to, whether the name of another HTML file on your site, or a URL of another site), and specify the text that the user will see. 

The browser will take care of underlining the text, and changing it to a different color, just like other links you've seen around the web.

----

### For reference:
```html
<img src="your-filename-here" />
<a href="your-url-or-filename-here">Text of the link</a>
```
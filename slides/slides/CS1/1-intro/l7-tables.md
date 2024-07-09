---
marp: true
theme: gradient
footer: Dominic Canora
paginate: true
headingDivider: 2
---

# Tables <!-- _class: title -->

# What's a table?
It looks like this:
|Column A Header|Column B Header|Column C Header|
|---|---|---|
|Row 1 Col A Data|Row 1 Col B Data|Row 1 Col C Data|
|Row 2 Col A Data|Row 2 Col B Data|Row 2 Col C Data|
|Row 3 Col A Data|Row 3 Col B Data|Row 3 Col C Data|

# Tables
### The HTML
```html
<table>
    <tr>
        <th>Column A</th>
        <th>Column B</th>
    </tr>
    <tr>
        <td>1</td>
        <td>2</td>
    </tr>
    <tr>
        <td>3</td>
        <td>4</td>
    </tr>
</table>
```

# Tables
### The Result
|Column A|Column B|
|---|---|
|1|2|
|3|4|

# Key Points
* The outermost element for a table is `table`
* A `table` element contains many `tr` (table row) elements
* A `tr` element contains many `th` (table header) or `td` (table data) elements
* Every `tr` should have the same number of cells

# You try!
Add a third page to your "About Me" site that includes your class schedule. Include the period number, the course name, and the teacher for each class. 

**Once you're finished, please review and submit the "About Me Checkpoint 1" assignment on Canvas**
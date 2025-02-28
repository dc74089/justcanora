<style>
td {
    border: thin solid white;
}
</style>

# Tables

----

# What's a table?
It looks like this:

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
    <tr></tr>
</table>
---

## Tables
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

----

# Key Points
* The outermost element for a table is `table`
* A `table` element contains many `tr` (table row) elements
* A `tr` element contains many `th` (table header) or `td` (table data) elements
* Every `tr` should have the same number of cells

---

# You try!
Add a page to your "About Me" site that includes your class schedule. Include the period number, the course name, and the teacher for each class.
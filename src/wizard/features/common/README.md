
## RegexTree

`RegexLeaf` is a leaf node without children.

`RegexTree` is defined recursively and consists of branches (children) as follows:
1. A single branch that contains a list of `RegexTree` or `RegexLeaf` instances.
2. Multiple branches, each possibly a `RegexTree` or a `RegexLeaf`.

As illustrated in the image below, `float` is a `RegexTree` with three branches (children), each of which is also a `RegexTree`. Taking `integer_dot_digit` as an example: it consists of one branch that includes two `RegexLeaf` nodes — `dot` and `digits` — along with one `RegexTree` named `integers`. The `integers` tree itself has two branches, each containing two `RegexLeaf` nodes: `digits` and `thousand_digits`.

![float](../../../../assets/float.jpg "float") 


Every intermediate variable defined in the class `IsNumBase` and its subclasses is a `RegexTree`, as depicted in the image above. In this visualization, a bright color denotes multiple branches, while a dark color signifies a single branch containing a list. The color blue represents a `RegexTree`, and the color green represents a `RegexLeaf`.


## Match the String

A `RegexTree` can be transformed into a regular expression to match strings looking like numbers. The conversion of a `RegexTree` to a regular expression is based on the following rules:

1. A `RegexLeaf` is directly converted into a regular expression.
2. If a `RegexTree` contains a single branch with a list of `RegexTree` or `RegexLeaf` instances, concatenate the regular expressions of these instances.
3. For multiple branches, each potentially being a `RegexTree` or a `RegexLeaf`, combine their regular expressions using the `|` character between every two branches.

## Convert the Matched Result into a Number

Once a string looking like numbers is identified as a numalike string, the next challenge is to convert it into an actual number. This process becomes particularly complex with irregular strings such as '(¥122,333)' or '1 33/333'.

With the `RegexTree`, my life becomes easier. Recall that when matching the string, we concatenate instances within a single branch and select between branches using the `|` character. This allows us to determine precisely which path matches the string!

Note that certain structures recur within our data model. For instance, the `RegexTree` labeled `integers` appears twice, and the `RegexLeaf` labeled `digits` appears four times. To efficiently convert these to numbers, we can assign distinct handlers to each `RegexLeaf` and `RegexTree`.

The conversion process is structured as follows:
1. For multiple branches, apply the specific `to_number` handlers designated for each branch.
2. For a single branch that includes either a `RegexTree` or `RegexLeaf`, use Python's tokenizer when the format is recognizable, or otherwise, implement a custom handler as a fallback.
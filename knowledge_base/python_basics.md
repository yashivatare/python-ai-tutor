# Python Basics and First Steps

## Getting Ready

Before writing your first program, install Python and use a code editor such as Visual Studio Code.

Your first program:

```python
print("Hello, World!")
```

`print()` is a built-in function that displays text on the screen.

## Understanding Python Fundamentals

Variables:

```python
message = "Hello"
number = 10
price = 9.99
is_active = True
```

Basic math:

```python
x = 10
y = 3
print(x + y)
print(x - y)
print(x * y)
print(x / y)
```

String formatting:

```python
name = "John"
print(f"Welcome, {name}!")
```

User input:

```python
color = input("Enter your favorite color: ")
print("You like:", color)
```

## Making Decisions and Repeating Actions

### Conditional statements

```python
temperature = 30

if temperature > 25:
    print("It's hot!")
elif temperature == 25:
    print("Perfect weather.")
else:
    print("It's cold.")
```

### Loops

```python
for i in range(3):
    print("Loop number:", i)

n = 5
while n > 0:
    print("Countdown:", n)
    n -= 1
```

## Working With Data

Lists:

```python
items = ["pen", "book", "phone"]
print(items[0])
```

Dictionaries:

```python
student = {"name": "Alex", "age": 22}
print(student["name"])
```

Tuples:

```python
point = (4, 5)
```

Sets:

```python
unique = {1, 2, 3, 3}
print(unique)  # duplicates removed
```

## Reusing Code With Functions

```python
def add(a, b):
    return a + b

print(add(2, 3))
```

## Importing Libraries

```python
import random
print(random.randint(1, 10))
```

## Moving Forward

Once you're comfortable with the basics, explore:

- file handling  
- object-oriented programming  
- data science libraries  
- web development frameworks  
- automation tools  

Keep experimenting and building small Python programs to reinforce your learning.

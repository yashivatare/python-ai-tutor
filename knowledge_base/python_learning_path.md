# Python Learning Path

## Core Concepts and Skills

Welcome! This Python learning path guides you from complete beginner to confident programmer. You will start with the basics of writing Python code, then move toward more advanced skills such as data handling and object-oriented programming.

Begin by installing Python from the official website and setting up a code editor like Visual Studio Code. Your first program is typically:

```python
print("Hello, World!")
```

Next, learn Python fundamentals such as variables, strings, integers, floats, and booleans:

```python
name = "Alice"
age = 20
height = 5.7
is_student = True

print(name, age, height, is_student)
```

Learn basic math operations:

```python
a = 5
b = 3
print(a + b)
print(a * b)
print(a / b)
```

Format text using f-strings:

```python
language = "Python"
print(f"I am learning {language}!")
```

Take user input:

```python
name = input("Enter your name: ")
print(f"Hello, {name}!")
```

Learn decision making:

```python
age = 18
if age >= 18:
    print("You can vote!")
else:
    print("You are too young.")
```

Practice loops:

```python
for i in range(5):
    print("Number:", i)

count = 3
while count > 0:
    print("Countdown:", count)
    count -= 1
```

Study Python’s built-in data structures:

```python
# List
fruits = ["apple", "banana", "cherry"]

# Dictionary
person = {"name": "Alex", "age": 21}

# Tuple
coordinates = (10, 20)

# Set
unique_numbers = {1, 2, 3, 3}
```

Write reusable code with functions:

```python
def greet(name):
    return f"Hello, {name}!"

print(greet("Alice"))
```

Import modules:

```python
import math
print(math.sqrt(25))
```

Learn error handling:

```python
try:
    x = 10 / 0
except ZeroDivisionError:
    print("Cannot divide by zero!")
```

Work with files:

```python
with open("note.txt", "w") as f:
    f.write("Hello from Python!")
```

Explore object-oriented programming:

```python
class Dog:
    def __init__(self, name):
        self.name = name

    def bark(self):
        print(f"{self.name} says woof!")

d = Dog("Buddy")
d.bark()
```

Once you are comfortable with these foundations, choose a specialization path:

- **Web development:** Learn Flask or Django.
- **Data science / AI:** Learn Pandas, NumPy, Matplotlib, Scikit-learn, or TensorFlow.
- **Automation / scripting:** Use BeautifulSoup or Selenium.

Build small apps and projects — consistency is the key to mastering Python!

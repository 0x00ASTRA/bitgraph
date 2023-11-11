# file1.py

from module1 import some_function

class MyClass:
    def __init__(self, name):
        self.name = name

    def say_hello(self):
        print(f"Hello, {self.name}!")

def main():
    obj = MyClass("John")
    obj.say_hello()
    some_function()

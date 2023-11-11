# Bitgraph

A program for graphing the complex relationships within a codebase.

## Table of Contents

>### [Forward](#forward-💡)
>
>### [Intro](#intro-🚩)
>
>### [Proto Project Tree](#proto-project-tree)
>
>### [Architecture](#architecture-🏗️)
>>#### [Parser](#parser-🕷️)
>>#### [Nodes](#nodes-🔵)
>>#### [Edges](#edges-🔗)

### Forward 💡

I have always found it a hassle to keep track of the relationships within a codebase. This becomes even more apparent when contributing to a large codebase that you are foreign to. Further more modern (2023) implimentations of AI require a to build relationship within code to contribute. With that in mind, I decided to create a program to handle these requirements and out came Bitgraph.

---

### Intro 🚩

Bitgraph is designed to automatically parse a codebase and model the complex relationships that exist within the code. This includes but isn't limited to: function creation, class creation, variable creation, function calls, class methods, class inheritance and more. The idea is to build a map of how a codebase works to make it easier to understand and modify.

---

### Proto Project Tree 🌴

```plaintext
bitgraph/
│
├── src/
│   ├── __init__.py
│   ├── parser.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── function_node.py
│   │   ├── class_node.py
│   │   ├── variable_node.py
│   │   └── module_node.py
│   ├── edges/
│   │   ├── __init__.py
│   │   ├── function_call_edge.py
│   │   ├── method_call_edge.py
│   │   ├── inheritance_edge.py
│   │   ├── assignment_edge.py
│   │   ├── global_variable_edge.py
│   │   └── attribute_edge.py
│   └── graph_builder.py
│
├── tests/
│   ├── __init__.py
│   ├── test_parser.py
│   ├── nodes/
│   │   ├── __init__.py
│   │   ├── test_function_node.py
│   │   ├── test_class_node.py
│   │   ├── test_variable_node.py
│   │   └── test_module_node.py
│   ├── edges/
│   │   ├── __init__.py
│   │   ├── test_function_call_edge.py
│   │   ├── test_method_call_edge.py
│   │   ├── test_inheritance_edge.py
│   │   ├── test_assignment_edge.py
│   │   ├── test_global_variable_edge.py
│   │   └── test_attribute_edge.py
│   └── test_graph_builder.py
│
├── db/
│   ├── codebase1.graphdb
│   └── codebase2.graphdb
│
├── main.py
└── requirements.txt
```

---

### Architecture 🏗️

#### Parser 🕷️

> Python Class

```python
class Parser:
    def __init__(self):
        pass
    
    def parse_file(file_path: str)
        # load the file
        with open(file_path, 'r') as f:
            file = f.read()
```

#### Nodes 🔵

#### Edges 🔗

---

### Usage

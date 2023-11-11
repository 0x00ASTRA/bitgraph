import ast
import os
from neo4j import GraphDatabase
from src.enums import NodeType, EdgeType

class CodebaseParser:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> None:
        self.driver = GraphDatabase.driver(uri=neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.custom_ignore_list = [
            "__pycache__",  # Example directory to ignore
            "venv",
            "neo4j",         # Example directory to ignore
            ".git",         # Example directory to ignore
            ".DS_Store",    # Example file to ignore
            "Makefile"  # Example file to ignore
        ]

    def populate_codebase(self, codebase_path: str) -> None:
        with self.driver.session() as session:
            for root, dirs, files in os.walk(codebase_path):
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    if self.should_ignore(full_path):
                        continue
                    session.run(
                        "MERGE (dir:Directory {path: $path})",
                        path=full_path
                    )
                
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    if self.should_ignore(full_path):
                        continue
                    session.run(
                        "MERGE (file:File {path: $path})",
                        path=full_path
                    )
                    # Create a relationship between directory and file
                    session.run(
                        "MATCH (dir:Directory {path: $dir_path}), (file:File {path: $file_path}) "
                        "MERGE (dir)-[:CONTAINS]->(file)",
                        dir_path=os.path.dirname(full_path), file_path=full_path
                    )

    def parse_codebase(self, codebase_path: str) -> None:
        with self.driver.session() as session:
            for root, dirs, files in os.walk(codebase_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    self.parse_file(session, file_path)

    def parse_file(self, session, file_path: str) -> None:
        # check if its a python file
        if not file_path.endswith(".py"):
            return
        with open(file_path, 'r') as f:
            code: str = f.read()

        tree: ast.AST = ast.parse(code, filename=file_path)
        self.process_tree(session, tree, file_path)

    def should_ignore(self, path):
        """Check if the path matches any entry in the ignore list."""
        for entry in self.custom_ignore_list:
            if entry in path:
                return True
        return False

    def process_tree(self, session, tree: ast.AST, file_path: str) -> None:
        if self.should_ignore(file_path):
            return  # Skip processing this file
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                self.process_function(session, node, file_path)
                self.process_function_calls(session, node, file_path)
                self.process_function_returns(session, node, file_path)

            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                self.handle_import(session, node, file_path)

            elif isinstance(node, ast.ClassDef):
                    self.process_class(session, node, file_path)
                    self.process_class_inheritance(session, node, file_path)
            
            elif isinstance(node, ast.Assign):
                self.process_assignment(session, node, file_path)
                self.process_function_parameters(session, node, file_path)

    def process_function(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        function_name: str = function_node.name

        # Check if the function is part of a class
        if hasattr(function_node, 'parent') and isinstance(function_node.parent, ast.ClassDef):
            class_name: str = function_node.parent.name

            # Create or merge the Function node
            session.run(
                "MERGE (function:Function {name: $name, type: $type, file: $file})",
                name=function_name, type=NodeType.FUNCTION.value, file=file_path
            )

            # Create or merge the Class node
            session.run(
                "MERGE (class:Class {name: $class_name, type: $type, file: $file})",
                class_name=class_name, type=NodeType.CLASS.value, file=file_path
            )

            # Create the BELONGS_TO relationship
            session.run(
                "MATCH (function:Function {name: $function_name, file: $file}), "
                "(class:Class {name: $class_name, file: $file}) "
                "MERGE (function)-[:BELONGS_TO]->(class)",
                function_name=function_name, class_name=class_name, file=file_path
            )
        else:
            # If the function is not part of a class, process it as usual
            session.run(
                "MERGE (function:Function {name: $name, type: $type, file: $file})",
                name=function_name, type=NodeType.FUNCTION.value, file=file_path
            )

            session.run(
                "MATCH (function:Function {name: $function_name, file: $file}), "
                "(file:File {path: $file}) "
                "MERGE (function)-[:BELONGS_TO]->(file)",
                function_name=function_name, file=file_path
            )


    def process_function_calls(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        for node in ast.walk(function_node):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    function_call_name = node.func.id
                    session.run(
                        "MATCH (caller:Function {name: $caller_name, file: $file}), "
                        "(callee:Function {name: $callee_name, file: $file}) "
                        "MERGE (caller)-[:CALLS]->(callee)",
                        caller_name=function_node.name, callee_name=function_call_name, file=file_path
                    )

    def process_function_returns(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        for node in ast.walk(function_node):
            if isinstance(node, ast.Return):
                # Assuming a single return value for simplicity
                if isinstance(node.value, ast.Name):
                    returned_variable = node.value.id
                    session.run(
                        "MATCH (function:Function {name: $function_name, file: $file}), "
                        "(variable:Variable {name: $variable_name, file: $file}) "
                        "MERGE (function)-[:RETURNS]->(variable)",
                        function_name=function_node.name, variable_name=returned_variable, file=file_path
                    )

    def process_function_parameters(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        if not hasattr(function_node, 'args') or not function_node.args.args:
            return  # Skip if there are no arguments

        for arg in function_node.args.args:
            parameter_name = arg.arg
            session.run(
                "MATCH (function:Function {name: $function_name, file: $file}), "
                "(variable:Variable {name: $parameter_name, file: $file}) "
                "MERGE (function)-[:HAS_PARAMETER]->(variable)",
                function_name=function_node.name, parameter_name=parameter_name, file=file_path
            )


    # Modify process_class method
    def process_class(self, session, class_node: ast.ClassDef, file_path: str) -> None:
        class_name: str = class_node.name

        session.run(
            "MERGE (class:Class {name: $name, type: $type, file: $file})",
            name=class_name, type=NodeType.CLASS.value, file=file_path
        )

        session.run(
            "MATCH (class:Class {name: $class_name, file: $file}), (file:File {path: $file}) "
            "MERGE (class)-[:BELONGS_TO]->(file)",
            class_name=class_name, file=file_path
        )

        # Process methods within the class
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef):
                self.process_function(session, node, file_path)
                self.process_function_calls(session, node, file_path)


    def process_class_inheritance(self, session, class_node: ast.ClassDef, file_path: str) -> None:
        if not hasattr(class_node, 'bases') or not class_node.bases:
            return  # Skip if there are no bases

        for base_node in class_node.bases:
            if isinstance(base_node, ast.Name):
                base_class_name = base_node.id
                session.run(
                    "MATCH (derived:Class {name: $derived_name, file: $file}), "
                    "(base:Class {name: $base_name, file: $file}) "
                    "MERGE (derived)-[:INHERITS]->(base)",
                    derived_name=class_node.name, base_name=base_class_name, file=file_path
                )

    def process_assignment(self, session, assignment_node: ast.Assign, file_path: str) -> None:
        for target in assignment_node.targets:
            if isinstance(target, ast.Name):
                variable_name: str = target.id

                session.run(
                    "MERGE (variable:Variable {name: $name, type: $type, file: $file})",
                    name=variable_name, type=NodeType.VARIABLE.value, file=file_path
                )

                session.run(
                    "MATCH (variable:Variable {name: $variable_name, file: $file}), (file:File {path: $file}) "
                    "MERGE (variable)-[:BELONGS_TO]->(file)",
                    variable_name=variable_name, file=file_path
                )

    # Modify handle_import method
    def handle_import(self, session, import_node, file_path: str) -> None:
        if isinstance(import_node, ast.Import):
            for alias in import_node.names:
                module_name: str = alias.name
                imported_type = self.get_imported_type(module_name)
                self.create_import_relationship(session, module_name, file_path, imported_type)

        elif isinstance(import_node, ast.ImportFrom):
            module_name: str = import_node.module if import_node.module else ""
            for alias in import_node.names:
                if alias.name == "*":
                    # Handle "from module import *"
                    continue
                full_module_name = f"{module_name}.{alias.name}" if module_name else alias.name
                imported_type = self.get_imported_type(full_module_name)
                self.create_import_relationship(session, full_module_name, file_path, imported_type)

    def get_imported_type(self, import_node) -> str:
        if isinstance(import_node, ast.Import):
            # Handle import statements
            return NodeType.MODULE.value

        elif isinstance(import_node, ast.ImportFrom):
            # Handle import-from statements
            module_name: str = import_node.module if import_node.module else ""
            full_module_name = f"{module_name}.{import_node.names[0].name}" if module_name else import_node.names[0].name

            # Check if the imported item is an enum.Enum
            try:
                imported_item = eval(full_module_name)
                if isinstance(imported_item, enum.Enum):
                    return NodeType.ENUM.value
            except (NameError, AttributeError):
                pass

            # If the module or object is not an enum, consider it as a class
            return NodeType.CLASS.value

        # Default to unknown if the type cannot be determined
        return NodeType.UNKNOWN.value




    def create_import_relationship(self, session, module_name: str, file_path: str, imported_type: str) -> None:
        result = session.run(
            "MATCH (importedItem {path: $module_name, type: $imported_type}) RETURN importedItem",
            module_name=module_name, imported_type=imported_type
        )

        if result.single():
            session.run(
                "MATCH (importedItem {path: $module_name, type: $imported_type}), "
                "(file:File {path: $file_path}) "
                "MERGE (file)-[:IMPORTS]->(importedItem)",
                module_name=module_name, imported_type=imported_type, file_path=file_path
            )
        else:
            # Create the importedItem node if it doesn't exist
            session.run(
                "MERGE (importedItem {path: $module_name, type: $imported_type})",
                module_name=module_name, imported_type=imported_type
            )

            # Create the IMPORTS relationship
            session.run(
                "MATCH (file:File {path: $file_path}), "
                "(importedItem {path: $module_name, type: $imported_type}) "
                "MERGE (file)-[:IMPORTS]->(importedItem)",
                file_path=file_path, module_name=module_name, imported_type=imported_type
            )


# Usage:
# parser = CodebaseParser(neo4j_uri, neo4j_user, neo4j_password, db_name="test_db")
# parser.populate_codebase("your_codebase_path")
# parser.parse_codebase("your_codebase_path")

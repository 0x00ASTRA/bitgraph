import ast
import os
from neo4j import GraphDatabase
from src.enums import NodeType, EdgeType

class CodebaseParser:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> None:
        # Initialize Neo4j driver
        self.driver = GraphDatabase.driver(uri=neo4j_uri, auth=(neo4j_user, neo4j_password))
        # Define a custom ignore list for directories and files
        self.custom_ignore_list = [
            "__pycache__",
            "venv",
            "neo4j",
            ".git",
            ".DS_Store",
            "Makefile"
        ]

    def populate_codebase(self, codebase_path: str) -> None:
        """
        Populates the Neo4j database with nodes representing files and directories in the codebase.
        Also creates relationships between directories and files.
        """
        with self.driver.session() as session:
            for root, dirs, files in os.walk(codebase_path):
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    if self.should_ignore(full_path):
                        continue
                    # Create a node for the directory
                    session.run(
                        "MERGE (dir:Directory {path: $path})",
                        path=full_path
                    )
                
                for file_name in files:
                    full_path = os.path.join(root, file_name)
                    if self.should_ignore(full_path):
                        continue
                    # Create a node for the file
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
        """
        Parses the codebase and populates the graph database with relationships between different entities.
        """
        with self.driver.session() as session:
            for root, _, files in os.walk(codebase_path):
                for file_name in files:
                    file_path = os.path.join(root, file_name)
                    self.parse_file(session, file_path)

    def parse_file(self, session, file_path: str) -> None:
        """
        Parses an individual Python file and processes its AST.
        """
        if not file_path.endswith(".py"):
            return
        with open(file_path, 'r') as f:
            code: str = f.read()

        tree: ast.AST = ast.parse(code, filename=file_path)
        self.process_tree(session, tree, file_path)

    def should_ignore(self, path):
        """
        Checks if the given path matches any entry in the ignore list.
        """
        for entry in self.custom_ignore_list:
            if entry in path:
                return True
        return False

    def process_tree(self, session, tree: ast.AST, file_path: str) -> None:
        """
        Processes the AST of a Python file and creates nodes and relationships based on its structure.
        """
        if self.should_ignore(file_path):
            return  # Skip processing this file
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                # Process function definitions
                self.process_function(session, node, file_path)
                self.process_function_calls(session, node, file_path)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                # Handle imports
                self.handle_import(session, node, file_path)
            elif isinstance(node, ast.ClassDef):
                # Process class definitions
                self.process_class(session, node, file_path)
            elif isinstance(node, ast.Assign):
                # Process assignments
                self.process_assignment(session, node, file_path)
            elif isinstance(node, ast.Return):
                # Process return statements
                self.process_return(session, node, file_path)
            # Add more conditions for other AST nodes

    def process_function(self, session, function_node: ast.FunctionDef, file_path: str, class_name: str=None) -> None:
        """
        Processes a function definition and creates nodes and relationships.
        """
        function_name: str = function_node.name
        # Create a node for the function
        session.run(
            "MERGE (function:Function {name: $name, type: $type, file: $file})",
            name=function_name, type=NodeType.FUNCTION.value, file=file_path
        )
        # Create a relationship between the function and the file
        if class_name is not None:
            session.run(
                "MATCH (class:Class {name: $class_name}), (function:Function {name: $function_name, file: $file}) "
                "MERGE (class)-[:BELONGS_TO]->(function)",
                class_name=class_name, function_name=function_name, file=file_path
            )
        elif hasattr(function_node, 'parent') and isinstance(function_node.parent, ast.ClassDef):
            # Create BELONGS_TO relationship between class and method
            method_name: str = function_node.name
            session.run(
                "MATCH (method:Function {name: $method_name, file: $file}), (class:Class {name: $class_name, file: $file}) "
                "MERGE (method)-[:BELONGS_TO]->(class)",
                method_name=method_name, class_name=class_name, file=file_path
            )
        else:
            session.run(
                "MATCH (function:Function {name: $function_name, file: $file}), (file:File {path: $file}) "
                "MERGE (function)-[:BELONGS_TO]->(file)",
                function_name=function_name, file=file_path
            )

    def is_nested_function(self, function_node):
        # Check if the function is nested within another function or a class
        return any(isinstance(node, (ast.FunctionDef, ast.ClassDef)) for node in function_node.body)

    def process_function_calls(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        """
        Processes function calls within a function and creates relationships.
        """
        for node in ast.walk(function_node):
            if isinstance(node, ast.Call):
                self._handle_function_call(session, function_node, node, file_path)

    def _handle_function_call(self, session, caller_function_node, call_node, file_path: str) -> None:
        """
        Handles the relationships for a function call within a function.
        """
        if isinstance(call_node.func, ast.Name):
            callee_name = call_node.func.id
            self._create_function_call_relationship(session, caller_function_node.name, callee_name, file_path)

    def _create_function_call_relationship(self, session, caller_name: str, callee_name: str, file_path: str) -> None:
        """
        Creates a CALLS relationship between functions for function calls.
        """
        session.run(
            "MATCH (caller:Function {name: $caller_name, file: $file}), "
            "(callee:Function {name: $callee_name, file: $file}) "
            "MERGE (caller)-[:CALLS]->(callee)",
            caller_name=caller_name, callee_name=callee_name, file=file_path
        )
        # Add similar methods for processing other AST nodes (imports, classes, assignments, etc.)

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

                # Create BELONGS_TO relationship between class and method
                method_name: str = node.name
                session.run(
                    "MATCH (method:Function {name: $method_name, file: $file}), (class:Class {name: $class_name, file: $file}) "
                    "MERGE (method)-[:BELONGS_TO]->(class)",
                    method_name=method_name, class_name=class_name, file=file_path
                )

            elif isinstance(node, ast.Assign):
                # Process attribute assignments within the class
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        variable_name: str = target.id  # Extracting the name from the target
                        session.run(
                            "MERGE (variable:Variable {name: $variable_name, type: $type, file: $file})",
                            variable_name=variable_name, type=NodeType.VARIABLE.value, file=file_path
                        )

                        session.run(
                            "MATCH (variable:Variable {name: $variable_name, file: $file}), (class:Class {name: $class_name, file: $file}) "
                            "MERGE (variable)-[:BELONGS_TO]->(class)",
                            variable_name=variable_name, class_name=class_name, file=file_path
                        )

    
    def process_assignment(self, session, assignment_node: ast.Assign, file_path: str, class_name: str=None) -> None:
        for target in assignment_node.targets:
            if isinstance(target, ast.Name):
                attribute_name: str = target.id
                if class_name is not None:
                    session.run(
                        "MATCH (attribute:Attribute {name: $attribute_name, file: $file}), (class:Class {name: $class_name, file: $file}) "
                        "MERGE (attribute)-[:BELONGS_TO]->(class)",
                        attribute_name=attribute_name, class_name=class_name, file=file_path
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

    def process_return(self, session, return_node: ast.Return, file_path: str) -> None:
        """
        Processes a return statement within a function and creates nodes and relationships.
        """
        if isinstance(return_node.value, ast.Name):
            # If the return value is a variable, create a node for the variable
            variable_name: str = return_node.value.id
            session.run(
                "MERGE (variable:Variable {name: $name, type: $type, file: $file})",
                name=variable_name, type=NodeType.VARIABLE.value, file=file_path
            )
            # Create a relationship between the variable and the file
            session.run(
                "MATCH (variable:Variable {name: $variable_name, file: $file}), (file:File {path: $file}) "
                "MERGE (variable)-[:BELONGS_TO]->(file)",
                variable_name=variable_name, file=file_path
            )


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
# parser = CodebaseParser(neo4j_uri, neo4j_user, neo4j_password)
# parser.populate_codebase("your_codebase_path")
# parser.parse_codebase("your_codebase_path")

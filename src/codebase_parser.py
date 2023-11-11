from pyflakes import api
from pyflakes.reporter import Reporter
from neo4j import GraphDatabase
import ast
from src.enums import NodeType, EdgeType
from halo import Halo

class CodebaseParser:
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str) -> None:
        self.driver = GraphDatabase.driver(uri=neo4j_uri, auth=(neo4j_user, neo4j_password))


    @Halo(text="Parsing codebase...", spinner="dots")
    def parse_file(self, file_path: str) -> None:
        with open(file_path, 'r') as f:
            code: str = f.read()

        tree: ast.AST = ast.parse(code, filename=file_path)
        self.process_tree(tree, file_path)

    def process_tree(self, tree: ast.AST, file_path: str) -> None:
        with self.driver.session() as session:
            session.run(
                "MERGE (file:File {path: $path})",
                path=file_path
            )

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    self.process_function(session, node, file_path)
                    self.process_function_calls(session, node, file_path)
                elif isinstance(node, ast.ClassDef):
                    self.process_class(session, node, file_path)
                elif isinstance(node, ast.Assign):
                    self.process_assignment(session, node, file_path)
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    success = self.process_import(session, node, file_path)
                    if success:
                        self.analyze_imports(file_path)

    def process_function(self, session, function_node: ast.FunctionDef, file_path: str) -> None:
        function_name: str = function_node.name
        arguments: list = [arg.arg for arg in function_node.args.args]

        session.run(
            "MERGE (function:Function {name: $name, type: $type, file: $file})",
            name=function_name, type=NodeType.FUNCTION.value, file=file_path
        )

        session.run(
            "MATCH (function:Function {name: $function_name, file: $file}), (file:File {path: $file}) "
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

    def process_import(self, session, import_node, file_path: str) -> bool:
        success = False
        if isinstance(import_node, ast.Import):
            for alias in import_node.names:
                module_name: str = alias.name
                success = self.create_import_relationship(session, module_name, file_path)

        elif isinstance(import_node, ast.ImportFrom):
            module_name: str = import_node.module if import_node.module else ""
            for alias in import_node.names:
                if alias.name == "*":
                    # Handle "from module import *"
                    continue
                success = self.create_import_relationship(session, f"{module_name}.{alias.name}", file_path)

        return success

    def create_import_relationship(self, session, module_name: str, file_path: str) -> bool:
        try:
            session.run(
                "MERGE (module:Module {name: $name, type: $type, file: $file})",
                name=module_name, type=NodeType.MODULE.value, file=file_path
            )

            session.run(
                "MATCH (module:Module {name: $module_name, file: $file}), (file:File {path: $file}) "
                "MERGE (module)-[:IMPORTS]->(file)",
                module_name=module_name, file=file_path
            )
            return True
        except Exception as e:
            # Handle exceptions if needed
            return False

    def analyze_imports(self, file_path: str) -> None:
        with open(file_path, 'r') as f:
            code: str = f.read()

        tree, w = api.parse(code, filename=file_path)
        self.process_tree(tree, file_path)

# Usage:
# parser = CodebaseParser(neo4j_uri, neo4j_user, neo4j_password, db_name="test_db")
# parser.parse_file("your_file_path.py")
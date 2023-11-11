import unittest
from unittest.mock import patch, MagicMock
from neo4j import GraphDatabase
from src.codebase_parser import CodebaseParser
from src.enums import NodeType

class TestCodebaseParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.neo4j_uri = "bolt://localhost:7687"  # Replace with your Neo4j URI
        cls.neo4j_user = "neo4j"  # Replace with your Neo4j username
        cls.neo4j_password = "password"  # Replace with your Neo4j password

    @patch("src.codebase_parser.GraphDatabase.driver")
    def test_parse_file(self, mock_driver):
        mock_session = mock_driver().session.return_value
        parser = CodebaseParser(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

        # Replace 'test_mock_codebase/file1.py' with the path to your mock codebase
        parser.parse_file("mock_codebase/file1.py")

        # Assertions for file parsing
        mock_session.run.assert_any_call(
            "MERGE (file:File {path: $path})",
            path="mock_codebase/file1.py"
        )

        # Assertions for function parsing
        mock_session.run.assert_any_call(
            "MERGE (function:Function {name: $name, type: $type, file: $file})",
            name="main", type=NodeType.FUNCTION.value, file="mock_codebase/file1.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (function:Function {name: $function_name, file: $file}), (file:File {path: $file}) "
            "MERGE (function)-[:BELONGS_TO]->(file)",
            function_name="main", file="mock_codebase/file1.py"
        )

        # Assertions for class parsing
        mock_session.run.assert_any_call(
            "MERGE (class:Class {name: $name, type: $type, file: $file})",
            name="MyClass", type=NodeType.CLASS.value, file="mock_codebase/file1.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (class:Class {name: $class_name, file: $file}), (file:File {path: $file}) "
            "MERGE (class)-[:BELONGS_TO]->(file)",
            class_name="MyClass", file="mock_codebase/file1.py"
        )

    @patch("src.codebase_parser.GraphDatabase.driver")
    def test_process_function(self, mock_driver):
        mock_session = mock_driver().session.return_value
        parser = CodebaseParser(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

        function_node = MagicMock()
        function_node.name = "test_function"

        parser.process_function(mock_session, function_node, "mock_codebase/file1.py")

        # Assertions for processing a function
        mock_session.run.assert_any_call(
            "MERGE (function:Function {name: $name, type: $type, file: $file})",
            name="test_function", type=NodeType.FUNCTION.value, file="mock_codebase/test_file.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (function:Function {name: $function_name, file: $file}), (file:File {path: $file}) "
            "MERGE (function)-[:BELONGS_TO]->(file)",
            function_name="test_function", file="mock_codebase/file1.py"
        )

    @patch("src.codebase_parser.GraphDatabase.driver")
    def test_process_class(self, mock_driver):
        mock_session = mock_driver().session.return_value
        parser = CodebaseParser(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

        class_node = MagicMock()
        class_node.name = "TestClass"

        parser.process_class(mock_session, class_node, "mock_codebase/file1.py")

        # Assertions for processing a class
        mock_session.run.assert_any_call(
            "MERGE (class:Class {name: $name, type: $type, file: $file})",
            name="TestClass", type=NodeType.CLASS.value, file="mock_codebase/file1.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (class:Class {name: $class_name, file: $file}), (file:File {path: $file}) "
            "MERGE (class)-[:BELONGS_TO]->(file)",
            class_name="TestClass", file="mock_codebase/file1.py"
        )

    @patch("src.codebase_parser.GraphDatabase.driver")
    def test_process_assignment(self, mock_driver):
        mock_session = mock_driver().session.return_value
        parser = CodebaseParser(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

        assignment_node = MagicMock()

        # Replace 'test_mock_codebase/test_file.py' with the path to your mock codebase
        parser.process_assignment(mock_session, assignment_node, "mock_codebase/file1.py")

        # Assertions for processing an assignment
        # Replace 'variable_name' with the expected variable name
        mock_session.run.assert_any_call(
            "MERGE (variable:Variable {name: $name, type: $type, file: $file})",
            name="variable_name", type=NodeType.VARIABLE.value, file="mock_codebase/file1.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (variable:Variable {name: $variable_name, file: $file}), (file:File {path: $file}) "
            "MERGE (variable)-[:BELONGS_TO]->(file)",
            variable_name="variable_name", file="mock_codebase/file1.py"
        )


    @patch("src.codebase_parser.GraphDatabase.driver")
    def test_process_import(self, mock_driver):
        mock_session = mock_driver().session.return_value
        parser = CodebaseParser(self.neo4j_uri, self.neo4j_user, self.neo4j_password)

        import_node = MagicMock()

        # Replace 'test_mock_codebase/test_file.py' with the path to your mock codebase
        parser.process_import(mock_session, import_node, "mock_codebase/file1.py")

        # Assertions for processing an import
        # Replace 'module_name' with the expected module name
        mock_session.run.assert_any_call(
            "MERGE (module:Module {name: $name, type: $type, file: $file})",
            name="module_name", type=NodeType.MODULE.value, file="mock_codebase/file1.py"
        )
        mock_session.run.assert_any_call(
            "MATCH (module:Module {name: $module_name, file: $file}), (file:File {path: $file}) "
            "MERGE (module)-[:BELONGS_TO]->(file)",
            module_name="module_name", file="mock_codebase/file1.py"
        )


if __name__ == "__main__":
    unittest.main()

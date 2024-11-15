import ast
import builtins


class NameCollector(ast.NodeVisitor):
    def __init__(self):
        self.scopes = [set()]
        self.used_names = set()

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Store):
            # Name is being assigned to; add to current scope
            self.scopes[-1].add(node.id)
        elif isinstance(node.ctx, ast.Load):
            # Name is being used; add to used names
            self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.scopes[-1].add(name.split('.')[0])

    def visit_ImportFrom(self, node):
        for alias in node.names:
            name = alias.asname if alias.asname else alias.name
            self.scopes[-1].add(name)

    def visit_ExceptHandler(self, node):
        if node.name:
            self.scopes[-1].add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node):
        # Add class name to current scope
        self.scopes[-1].add(node.name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        # Add function name to current scope
        self.scopes[-1].add(node.name)
        self.generic_visit(node)


def get_undefined_references(code):
    # Parse the code into an AST
    tree = ast.parse(code)
    collector = NameCollector()
    collector.visit(tree)

    # Combine all defined names from all scopes
    defined_names = set().union(*collector.scopes)

    # Undefined names are used names not in defined names or builtins
    undefined_names = collector.used_names - defined_names - set(dir(builtins))
    return list(undefined_names)


if __name__ == "__main__":
    code = """
def foo():
    pass

foo()
"""
    undefined_refs = get_undefined_references(code)
    print("Undefined references:", undefined_refs)

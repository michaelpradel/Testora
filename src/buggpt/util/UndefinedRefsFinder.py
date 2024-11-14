import ast
import builtins


def get_undefined_references(code):

    class NameCollector(ast.NodeVisitor):
        def __init__(self):
            self.used_names = set()
            self.scopes = [set()]  # Stack of scopes

        def visit_FunctionDef(self, node):
            # Add function name to current scope
            self.scopes[-1].add(node.name)
            # Create new scope for the function
            self.scopes.append(set())
            # Add parameters to the new scope
            for arg in node.args.args:
                self.scopes[-1].add(arg.arg)
            # Visit the body of the function
            self.generic_visit(node)
            # Pop the function scope
            self.scopes.pop()

        def visit_ClassDef(self, node):
            # Add class name to current scope
            self.scopes[-1].add(node.name)
            # Create new scope for the class
            self.scopes.append(set())
            # Visit the body of the class
            self.generic_visit(node)
            # Pop the class scope
            self.scopes.pop()

        def visit_Lambda(self, node):
            # Create new scope for the lambda
            self.scopes.append(set())
            # Add parameters to the new scope
            for arg in node.args.args:
                self.scopes[-1].add(arg.arg)
            # Visit the body of the lambda
            self.generic_visit(node)
            # Pop the lambda scope
            self.scopes.pop()

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
# Example 5:
import numpy as np
from keras.layers import Rescaling

# Using Rescaling layer in a model
from keras.models import Sequential

model = Sequential()
model.add(Rescaling(scale=1.0 / 255.0, offset=0.0, input_shape=(3, 3)))
model.add(keras.layers.Flatten())

input_data_model = np.array([[[0, 0, 0], [127, 127, 127], [255, 255, 255]]])
output_data_model = model(input_data_model)

print("Example 5 - Using Rescaling in a Model:")
print("Input Data:\\n", input_data_model)
print("Output Data:\\n", output_data_model)
"""
    undefined_refs = get_undefined_references(code)
    print("Undefined references:", undefined_refs)
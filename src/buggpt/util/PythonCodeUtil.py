import libcst as cst


class FunctionExtractor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self):
        self.nodes_and_lines = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        start_pos = self.get_metadata(
            cst.metadata.PositionProvider, node).start
        end_pos = self.get_metadata(cst.metadata.PositionProvider, node).end
        self.nodes_and_lines.append((node, start_pos.line, end_pos.line))


class CallExtractor(cst.CSTVisitor):
    def __init__(self):
        self.callees = []

    def visit_Call(self, node: cst.Call) -> bool | None:
        if isinstance(node.func, cst.Attribute):
            self.callees.append(node.func.attr.value)
        elif isinstance(node.func, cst.Name):
            self.callees.append(node.func.value)
        else:
            raise ValueError("Unknown callee type")


def extract_target_function(code, patch_range):
    tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(tree)
    extractor = FunctionExtractor()
    wrapper.visit(extractor)

    function_code = None
    for node, start_line, end_line in extractor.nodes_and_lines:
        target_line = (patch_range[0] + patch_range[1]) / 2
        if start_line < target_line and target_line < end_line:
            if function_code is not None:
                raise ValueError(
                    "Multiple functions found in the patch range")
            module_with_node = cst.Module(body=[node])
            function_code = module_with_node.code

    return function_code


def is_parsable(code: str) -> bool:
    try:
        cst.parse_module(code)
    except cst.ParserSyntaxError as e:
        print(f"Syntax error:\n{e}")
        return False
    return True


def get_name_of_defined_function(code: str) -> str:
    tree = cst.parse_module(code)
    wrapper = cst.metadata.MetadataWrapper(tree)
    extractor = FunctionExtractor()
    wrapper.visit(extractor)

    function_nodes = [node for node, _, _ in extractor.nodes_and_lines]

    if len(function_nodes) != 1:
        print(
            f"Warning: {len(function_nodes)} functions found, using the first one")

    return function_nodes[0].name.value


def get_surrounding_class(code, patch_range, function_name):
    pass  # TODO implement


def extract_tests_of_fut(all_test_code, fut_name):
    tree = cst.parse_module(all_test_code)
    wrapper = cst.metadata.MetadataWrapper(tree)
    function_extractor = FunctionExtractor()
    wrapper.visit(function_extractor)

    test_functions = []
    for node, _, _ in function_extractor.nodes_and_lines:
        call_extractor = CallExtractor()
        node.visit(call_extractor)
        if fut_name in call_extractor.callees:
            module_with_node = cst.Module(body=[node])
            function_code = module_with_node.code
            test_functions.append(function_code)
    return "\n\n".join(test_functions)


class FunctionRemover(cst.CSTTransformer):
    def __init__(self, function_name: str):
        self.function_name = function_name

    def leave_FunctionDef(self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef) -> cst.FunctionDef:
        if updated_node.name.value == self.function_name:
            return cst.RemoveFromParent()
        return updated_node


def remove_function_with_name(code: str, function_name: str) -> str:
    tree = cst.parse_module(code)
    transformer = FunctionRemover(function_name)
    new_tree = tree.visit(transformer)
    return new_tree.code

    # wrapper = cst.metadata.MetadataWrapper(tree)
    # extractor = FunctionExtractor()
    # wrapper.visit(extractor)

    # function_nodes = [node for node, _, _ in extractor.nodes_and_lines]
    # function_nodes_with_matching_name = [
    #     n for n in function_nodes if n.name.value == function_name]

    # result = code
    # for n in function_nodes_with_matching_name:
    #     result = result.replace(n.code, "")
    # return result


def add_call_to_test_function(code: str):
    function_name = get_name_of_defined_function(code)
    return code + f"\n\n{function_name}()"

import libcst as cst


class FunctionExtractor(cst.CSTVisitor):
    METADATA_DEPENDENCIES = (cst.metadata.PositionProvider,)

    def __init__(self):
        self.nodes_and_lines = []

    def visit_FunctionDef(self, node: cst.FunctionDef) -> bool | None:
        start_pos = self.get_metadata(cst.metadata.PositionProvider, node).start
        end_pos = self.get_metadata(cst.metadata.PositionProvider, node).end
        self.nodes_and_lines.append((node, start_pos.line, end_pos.line))


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

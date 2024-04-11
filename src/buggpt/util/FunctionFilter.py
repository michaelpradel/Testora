from buggpt.prompts.SelfExplanatoryPrompt import SelfExplanatoryPrompt
import libcst as cst

from buggpt.llms.LLMCache import LLMCache
import buggpt.llms.OpenAIGPT as uncached_llm
llm = LLMCache(uncached_llm)


class UndefinedFinder(cst.CSTVisitor):
    def __init__(self, undefined_variables_locations, ranges):
        super().__init__()
        self.undefined_variables = []
        self.undefined_variables_locations = undefined_variables_locations
        self.ranges = ranges

    def visit_Attribute(self, node):
        for undefined_variable_location in self.undefined_variables_locations:
            variable, location = undefined_variable_location
            if isinstance(node.value, cst.Name) and node.value.value == variable:
                self.undefined_variables.append(
                    f'{node.value.value}.{node.attr.value}')
                break
        return node


def get_undefined_variables(src):
    undefined_variables = []  # using a list here to get a deterministic order

    ast = cst.parse_module(src)
    ast_wrapper = cst.metadata.MetadataWrapper(ast)
    scopes = ast_wrapper.resolve(cst.metadata.ScopeProvider).values()
    for scope in scopes:
        for access in scope.accesses:
            if len(access.referents) == 0:
                node = access.node
                undefined_variables.append(node.value)

    # remove duplicates
    undefined_variables = list(dict.fromkeys(undefined_variables))

    return undefined_variables


def get_undefined_attributes_methods(src):
    # using a list here to get a deterministic order
    undefined_variables_locations = []

    ast = cst.parse_module(src)
    ast_wrapper = cst.metadata.MetadataWrapper(ast)
    scopes = ast_wrapper.resolve(cst.metadata.ScopeProvider).values()
    ranges = ast_wrapper.resolve(cst.metadata.PositionProvider)
    for scope in scopes:
        for access in scope.accesses:
            if len(access.referents) == 0:
                node = access.node
                location = ranges[node].start
                undefined_variables_locations.append((node.value, location))

    undefined_finder = UndefinedFinder(undefined_variables_locations, ranges)
    ast_wrapper.visit(undefined_finder)

    undefined_attributes = undefined_finder.undefined_variables
    # remove duplicates
    undefined_attributes = list(dict.fromkeys(undefined_attributes))

    return undefined_attributes


def remove_based_on_undefined_references(fut_code):
    undefined_variables = get_undefined_variables(fut_code)
    undefined_attributes_and_methods = get_undefined_attributes_methods(
        fut_code)

    return len(undefined_variables) > 2 or len(undefined_attributes_and_methods) > 2


def remove_because_not_self_explanatory(fut_code):
    prompt = SelfExplanatoryPrompt(fut_code)
    raw_answer = llm.query(prompt)
    keep = prompt.parse_answer(raw_answer)
    return not keep

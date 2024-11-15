import libcst as cst


def get_undefined_references(src):
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


if __name__ == "__main__":
    code = """
def foo(l):
    l()

foo(lambda n: print(n), bar)
"""
    undefined_refs = get_undefined_references(code)
    print("Undefined references:", undefined_refs)

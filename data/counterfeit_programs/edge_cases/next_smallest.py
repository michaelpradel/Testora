def next_smallest(lst):
    """
    Return the 2nd smallest element of a list of integers
    Return None if there is no such element.
    next_smallest([2, 1, 3]) == 2
    next_smallest([1, 1]) == None
    """
    if len(lst) < 2:
        return None
    lst_copy = lst.copy()
    lst_copy.sort()
    return lst_copy[1]
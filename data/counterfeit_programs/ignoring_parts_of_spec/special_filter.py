def specialFilter(nums):
    """Write a function that takes an array of numbers as input and returns
    the number of elements in the array that are greater than 10 and both
    first and last digits of a number are odd (1, 3, 5, 7, 9).
    For example:
    specialFilter([15, -73, 14, -15]) => 1
    specialFilter([33, -2, -3, 45, 21, 109]) => 2
    """
    
    # Define a function that checks if the first and last digit of a number is odd
    def isSpecial(n):
        if n < 0: n = -n # make sure n is positive
        return n % 10 in [1, 3, 5, 7, 9] and n//10 % 10 in [1, 3, 5, 7, 9]
    
    # Use a list comprehension to filter the numbers and count the results
    return sum(1 for num in nums if num > 10 and isSpecial(num))
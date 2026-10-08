"""Pure bounded arithmetic contracts for CrossHair; no filesystem side effects."""


def first_index(a: int, b: int, c: int) -> int:
    """
    pre: 0 <= a <= 2 and 0 <= b <= 2 and 0 <= c <= 2
    post: 0 <= __return__ <= 2
    post: (a, b, c)[__return__] == c
    post: all((a, b, c)[i] != c for i in range(__return__))
    """
    return 0 if a == c else 1 if b == c else 2


def deliberately_last_index(a: int, b: int, c: int) -> int:
    """
    pre: 0 <= a <= 2 and 0 <= b <= 2 and 0 <= c <= 2
    post: all((a, b, c)[i] != c for i in range(__return__))
    """
    return 2

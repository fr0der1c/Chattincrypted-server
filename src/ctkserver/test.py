def _generate_random_code():
    import random
    seed = "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()_+=-"
    sa = []
    for i in range(80):
        sa.append(random.choice(seed))
    salt = ''.join(sa)
    print(salt)


if __name__ == '__main__':
    _generate_random_code()
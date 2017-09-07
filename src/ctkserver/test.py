count = 0
while True:
    try:
        count = count + 1
        print(count)
        if count == 1000:
            raise KeyError
    except KeyError:
        break

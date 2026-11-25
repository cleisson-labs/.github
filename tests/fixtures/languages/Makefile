analyze:
	cppcheck --enable=warning --error-exitcode=1 main.c

sanitize:
	$(CC) -Wall -Werror -fsanitize=address,undefined main.c -o smoke
	./smoke

coverage:
	$(CC) -Wall -Werror --coverage main.c -o smoke
	./smoke
	gcovr --fail-under-line 100

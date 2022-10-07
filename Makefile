NAME=tmp
TAG=latest
PORT=3000

doc-build:
	docker build -t $(NAME):$(TAG) .

doc-run:
	docker run -d -p $(PORT):80 --name $(NAME) --rm $(NAME):$(TAG)

doc-stop:
	docker stop $(NAME)

doc-rmi:
	docker rmi $(NAME):$(TAG)

doc-test:
	python3 httptest.py localhost $(PORT)
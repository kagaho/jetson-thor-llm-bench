.PHONY: test doctor quick reasoning context

test:
	python3 -m unittest discover -s tests -v

doctor:
	python3 -m thorbench doctor

quick:
	python3 -m thorbench bench --suite quick --runs 3

reasoning:
	python3 -m thorbench bench --suite reasoning --runs 2

context:
	python3 -m thorbench bench --suite context --runs 1 --warmup 0

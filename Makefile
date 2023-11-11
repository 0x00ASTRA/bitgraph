NEO4J_CONTAINER_NAME = my_neo4j
NEO4J_PASSWORD = mypassword

.PHONY: start-neo4j
start-neo4j:
	cd neo4j && docker-compose up -d

.PHONY: stop-neo4j
stop-neo4j:
	cd neo4j && docker-compose down

.PHONY: logs-neo4j
logs-neo4j:
	docker logs $(NEO4J_CONTAINER_NAME)

.PHONY: clean
clean:
	rm -rf neo4j/data neo4j/logs neo4j/import neo4j/plugins

.PHONY: test
test:
	python -m unittest discover tests

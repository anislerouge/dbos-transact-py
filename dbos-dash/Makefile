.PHONY: install install-web server dashboard dev test build-web

install:
	pdm install

install-web:
	cd web && npm install

server:
	pdm run python -m dbos_dash

dashboard:
	cd web && npm run dev

dev:
	@echo "Start backend and frontend in parallel"
	@trap 'kill 0' EXIT; \
		pdm run python -m dbos_dash & \
		cd web && npm run dev &  \
		wait

test:
	pdm run pytest tests/ -v

build-web:
	cd web && npm run build

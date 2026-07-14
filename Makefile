.PHONY: secrets test eval ci doctor ci-hermetic ci-dbt12 vendor-check lint typecheck
secrets:
	uv run python scripts/check_secrets.py .
test: secrets
	uv run pytest -q
eval:
	uv run python -m eval.harness
doctor:
	uv run python scripts/env_doctor.py
ci: secrets test eval
ci-hermetic:
	uv run pytest -q
	uv run python -m eval.harness
	uv run python scripts/check_secrets.py .
ci-dbt12:
	PYTHONPATH=. uv run --no-project --with 'dbt-core==1.12.0b3' --with dbt-duckdb --with pytest --prerelease=allow -- pytest tests/e2e -v
vendor-check:
	bash scripts/check_vendor_updates.sh
lint:
	uv run ruff check .
	uv run ruff format --check .
typecheck:
	uv run mypy trust

PYTHON ?= python3

.PHONY: test lint demo

test:
	$(PYTHON) -m pytest --tb=short

lint:
	$(PYTHON) -m ruff check tools tests scripts
	$(PYTHON) -m ruff format --check tools tests scripts

demo:
	@mkdir -p reports
	@echo "== Drift checker: offline sample with deliberate drift =="
	$(PYTHON) tools/drift/checker.py \
	  --desired tools/drift/samples/desired-state.yaml \
	  --live tools/drift/samples/live-export.json \
	  --markdown reports/drift.md \
	  --json reports/drift.json \
	  --exit-zero
	@echo "== Expiry monitor: clock frozen at 2028-04-01 =="
	$(PYTHON) tools/expiry-monitor/monitor.py \
	  --inventory tools/expiry-monitor/inventory/lab.yaml \
	  --now 2028-04-01T00:00:00Z \
	  --markdown reports/expiry.md \
	  --json reports/expiry.json \
	  --exit-zero
	@echo "Reports written to reports/drift.md, reports/drift.json, reports/expiry.md, and reports/expiry.json"

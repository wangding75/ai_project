.PHONY: help progress check-stage advance schema-coverage lock-tests unlock-tests install-hooks

PROJECT ?= hermes
STAGE ?= 01-requirements
PY := python3

help:
	@echo "AI Project 工作流命令"
	@echo ""
	@echo "  make progress PROJECT=hermes          自动更新 <project>/PROGRESS.md"
	@echo "  make check-stage PROJECT=hermes STAGE=03-module-design"
	@echo "                                        验证某阶段产出清单"
	@echo "  make advance PROJECT=hermes           从当前阶段推进到下一阶段"
	@echo "  make schema-coverage PROJECT=hermes   检查 TDD 测试覆盖 schema"
	@echo "  make lock-tests PROJECT=hermes        锁定 stage 04 测试目录"
	@echo "  make unlock-tests PROJECT=hermes REASON=\"...\""
	@echo "                                        解锁测试目录（留审计）"
	@echo "  make install-hooks                    安装 git pre-commit hook"
	@echo ""
	@echo "常用示例："
	@echo "  make progress PROJECT=hermes"
	@echo "  make check-stage PROJECT=hermes STAGE=03-module-design"
	@echo "  make advance PROJECT=hermes"

progress:
	$(PY) scripts/update_progress.py $(PROJECT)

check-stage:
	$(PY) scripts/check_stage.py $(PROJECT) $(STAGE)

advance:
	$(PY) scripts/advance_stage.py $(PROJECT)

schema-coverage:
	$(PY) scripts/check_schema_coverage.py $(PROJECT)

lock-tests:
	bash scripts/lock_tests.sh $(PROJECT)/stages/04-development/tests

unlock-tests:
	@if [ -z "$(REASON)" ]; then echo "ERROR: REASON=\"...\" is required"; exit 1; fi
	bash scripts/unlock_tests.sh $(PROJECT)/stages/04-development/tests "$(REASON)"

install-hooks:
	git config core.hooksPath .githooks
	chmod +x .githooks/pre-commit
	@echo "✅ Git hooks installed (core.hooksPath=.githooks)"

check-all:
	@for p in hermes consilium; do \
		for s in 01-requirements 02-system-design 03-module-design 04-development 05-testing 06-deployment 07-operations; do \
			$(PY) scripts/check_stage.py $$p $$s || true; \
		done; \
	done

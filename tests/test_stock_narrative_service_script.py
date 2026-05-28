from scripts import run_stock_narrative_service


def test_run_stock_narrative_service_exposes_main():
    assert callable(run_stock_narrative_service.main)


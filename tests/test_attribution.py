from trust.manifest_loader import load_metrics

FIX = "tests/fixtures/manifests/two_model_derived"


def test_simple_metrics_owned_by_their_model():
    by = {m.name: m for m in load_metrics(FIX)}
    assert by["order_revenue"].owner_model == "fct_orders"
    assert by["refund_total"].owner_model == "fct_refunds"


def test_derived_metric_is_cross_model_unowned():
    by = {m.name: m for m in load_metrics(FIX)}
    assert by["net_revenue"].owner_model is None
    assert by["net_revenue"].type == "derived"

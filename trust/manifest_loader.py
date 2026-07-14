"""Reader over dbt's compiled target/semantic_manifest.json (DSI contract).
Both legacy (1.6-1.11) and latest (1.12+) specs compile to this identical shape,
so the engine is spec- and version-agnostic. The engine NEVER parses YAML."""
import json
import os
import re
from trust.normalized import NormalizedModel, NormalizedMetric


def _read_semantic_manifest(project_dir: str) -> dict:
    path = os.path.join(project_dir, "target", "semantic_manifest.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"No semantic manifest at {path}. Run `dbt parse` "
            f"(or trust.compile.compile_manifest) to generate it."
        )
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _map_model(sm: dict) -> NormalizedModel:
    entities = [
        {"name": e.get("name", ""), "type": e.get("type", "")}
        for e in (sm.get("entities") or [])
    ]
    dims = []
    for d in (sm.get("dimensions") or []):
        is_time = d.get("type") == "time"
        dims.append({
            "name": d.get("name", ""),
            "type": d.get("type", "categorical"),
            "is_time": is_time,
        })
    measures = [
        {"name": ms.get("name", ""), "agg": ms.get("agg", ""), "expr": ms.get("expr", "") or ""}
        for ms in (sm.get("measures") or [])
    ]
    name = sm.get("name", "")
    return NormalizedModel(
        name=name,
        source_file=name,           # DSI artifact carries no file path; name is the key
        spec="manifest",
        entities=entities,
        dimensions=dims,
        measures=measures,
        has_time_dimension=any(d["is_time"] for d in dims),
    )


def _measures_by_model(manifest: dict) -> dict:
    """measure_name -> {model, agg, expr}; first declaration wins (legacy shared-name)."""
    out: dict[str, dict] = {}
    for sm in (manifest.get("semantic_models") or []):
        if not isinstance(sm, dict):
            continue
        for ms in (sm.get("measures") or []):
            nm = ms.get("name")
            if nm and nm not in out:
                out[nm] = {"model": sm.get("name", ""),
                           "agg": ms.get("agg", ""),
                           "expr": ms.get("expr", "") or ""}
    return out


def _resolve_agg_expr(metric: dict, measures_by_model: dict):
    """Return (owner_model, agg, expr) for a metric from the manifest.
    Latest simple: type_params.metric_aggregation_params carries semantic_model+agg,
      expr is inline on type_params. Legacy simple: type_params.measure references a
      measure whose owning SM + agg + expr we look up. Non-simple: (None, "", "")."""
    tp = metric.get("type_params") or {}
    agg_params = tp.get("metric_aggregation_params")
    if agg_params:  # latest simple
        return agg_params.get("semantic_model"), agg_params.get("agg", "") or "", tp.get("expr", "") or ""
    measure = tp.get("measure")
    if isinstance(measure, dict) and measure.get("name"):  # legacy simple
        info = measures_by_model.get(measure["name"])
        if info:
            return info["model"], info["agg"], info["expr"]
        return None, "", ""
    return None, "", ""


def _ref_name(x):
    """numerator/denominator may be a str (metric name) or dict {name,...}."""
    if isinstance(x, dict):
        return x.get("name", "") or ""
    return x or ""


def _input_metric_names(tp: dict) -> list:
    names = []
    for m in (tp.get("metrics") or []):
        names.append(_ref_name(m))
    return sorted(n for n in names if n)


def _definition_norm(metric: dict, agg: str, expr: str) -> str:
    tp = metric.get("type_params") or {}
    mtype = metric.get("type", "") or ""
    if mtype == "simple":
        canon: dict[str, object] = {"type": "simple", "agg": agg or "", "expr": expr or ""}
    elif mtype == "ratio":
        canon = {"type": "ratio",
                 "numerator": _ref_name(tp.get("numerator")),
                 "denominator": _ref_name(tp.get("denominator"))}
    elif mtype == "cumulative":
        ctp = tp.get("cumulative_type_params") or {}
        # input metric may be under cumulative_type_params.metric (dbt 1.12 compiled shape)
        metric_ref = ctp.get("metric") or {}
        input_metric_name = _ref_name(metric_ref).strip().lower()
        # window is an object {count, granularity} under cumulative_type_params
        window_obj = ctp.get("window") or {}
        window_str = f"{window_obj.get('count', '')} {window_obj.get('granularity', '')}".strip().lower()
        grain = (ctp.get("grain_to_date") or "").strip().lower()
        canon = {
            "type": "cumulative",
            "input_metric": input_metric_name,
            "window": window_str,
            "grain_to_date": grain,
        }
    elif mtype == "derived":
        canon = {"type": "derived", "expr": (tp.get("expr") or "").strip().lower(), "metrics": _input_metric_names(tp)}
    elif mtype == "conversion":
        ctp = tp.get("conversion_type_params") or {}
        canon = {
            "type": "conversion",
            "base_metric": _ref_name(ctp.get("base_metric")).strip().lower(),
            "conversion_metric": _ref_name(ctp.get("conversion_metric")).strip().lower(),
            "window": (str(ctp.get("window") or "")).strip().lower(),
        }
    else:
        canon = {"type": mtype}
    s = json.dumps(canon, sort_keys=True, separators=(",", ":"))
    return re.sub(r"\s+", "", s).lower()


def _owner(metric: dict):
    return ((metric.get("config") or {}).get("meta") or {}).get("owner") or None


def load_metrics(project_dir: str) -> list:
    manifest = _read_semantic_manifest(project_dir)
    mbm = _measures_by_model(manifest)
    out = []
    for metric in (manifest.get("metrics") or []):
        if not isinstance(metric, dict):
            continue
        owner_model, agg, expr = _resolve_agg_expr(metric, mbm)
        out.append(NormalizedMetric(
            name=metric.get("name", ""),
            type=metric.get("type", "") or "",
            definition_norm=_definition_norm(metric, agg, expr),
            description=metric.get("description", "") or "",
            owner=_owner(metric),
            source_file=owner_model or metric.get("name", ""),
            owner_model=owner_model,
        ))
    return out


def load_models(project_dir: str) -> list:
    manifest = _read_semantic_manifest(project_dir)
    return [_map_model(sm) for sm in (manifest.get("semantic_models") or [])
            if isinstance(sm, dict)]

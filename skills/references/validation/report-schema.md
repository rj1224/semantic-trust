# Validation Report Schema

> Target: dbt-core 1.12+ | Last verified: 2026-04-23

The validation report is saved as `validation_report.json` in the model's directory. It captures CI gate results, trust score, per-document breakdown, naming compliance, and validation history.

## Schema

```json
{
  "model": "<model_name>",
  "owner": "<primary_owner — from dbt docs config.meta.owner>",
  "model_created_at": "<ISO timestamp — from catalog if available, else null>",
  "model_last_altered": "<ISO timestamp — from catalog if available, else null>",
  "generated_at": "<ISO timestamp — when docs were first generated>",
  "validated_at": "<ISO timestamp — when this report was last produced>",
  "validation_run": 1,
  "generated_by": "semantic-trust/document-semantics | semantic-trust/validate-semantics",
  "plugin_version": "0.4.0",
  "scoring_version": "v5",

  "ci_gates": {
    "structural": {
      "status": "pass",
      "checks_passed": 354,
      "checks_total": 354,
      "failures": []
    },
    "ownership": {
      "status": "fail",
      "checks_passed": 45,
      "checks_total": 88,
      "failures": [
        {
          "rule": "email_not_blank",
          "message": "business_owner is blank",
          "location": "semantic_models[0].config.meta.business_owner",
          "file": "fact_orders.yml"
        }
      ]
    },
    "completeness": {
      "status": "pass",
      "checks_passed": 3,
      "checks_total": 3,
      "failures": [],
      "info": []
    },
    "uniqueness": {
      "status": "pass",
      "checks_passed": 3,
      "checks_total": 3,
      "failures": []
    },
    "joinability": {
      "status": "pass",
      "checks_passed": 2,
      "checks_total": 2,
      "failures": []
    }
  },

  "trust_score": {
    "score": 80,
    "grade": "B",
    "breakdown": {
      "data_context": {
        "weight": 0.60,
        "score": 73,
        "weighted": 43.56,
        "checks_passed": 45,
        "checks_total": 62,
        "detail": "17 gaps: missing dimension descriptions and labels."
      },
      "data_quality": {
        "weight": 0.40,
        "score": 95,
        "weighted": 38.08,
        "checks_passed": 59,
        "checks_total": 62,
        "detail": "Strong. 3 gaps in entity relationships and defaults."
      }
    }
  },

  "documents": {
    "dbt_docs": {
      "file": "models/docs/fact/fact_orders.yml",
      "score": 88,
      "status": "pass",
      "checks_passed": 22,
      "checks_total": 25,
      "issues": [
        {
          "severity": "warning",
          "dimension": "data_quality",
          "rule": "fk_relationship_test",
          "message": "FK columns lack relationships tests pointing to valid ref() models",
          "location": "models[0].columns[3]"
        }
      ],
      "summary": "Well-structured fact table doc. Minor gaps in FK relationship tests."
    },
    "semantic_model": {
      "file": "models/semantics/supply/orders.yml",
      "score": 82,
      "status": "pass",
      "checks_passed": 24,
      "checks_total": 29,
      "issues": [],
      "summary": "Structurally sound with proper entity relationships."
    },
    "metrics": {
      "file": "models/semantics/supply/orders.yml",
      "note": "Metrics section in combined SM+metrics file",
      "score": 80,
      "status": "pass",
      "checks_passed": 20,
      "checks_total": 25,
      "issues": [],
      "summary": "Simple metrics well-defined."
    },
    "few_shot": {
      "file": "models/few_shot_examples/supply/fact_orders.json",
      "score": 90,
      "status": "pass",
      "checks_passed": 16,
      "checks_total": 18,
      "issues": [],
      "summary": "5 examples covering basic to hard difficulty."
    }
  },

  "naming_compliance": {
    "model_name": {
      "valid": true,
      "convention": "fact_[business_event]",
      "value": "fact_orders"
    },
    "columns": {
      "valid": true,
      "snake_case": true,
      "violations": []
    },
    "semantic_model_name": {
      "valid": true,
      "convention": "business_domain",
      "value": "orders"
    },
    "measure_names": {
      "valid": true,
      "violations": []
    },
    "metric_names": {
      "valid": true,
      "violations": []
    }
  },

  "validation_history": [
    {
      "run": 1,
      "timestamp": "<ISO timestamp>",
      "trust_score": 72,
      "grade": "C",
      "ci_gates_passed": false,
      "trigger": "initial_generation",
      "changes": "First validation after document generation"
    }
  ],

  "summary": {
    "total_issues": 3,
    "critical": 0,
    "warnings": 2,
    "info": 1,
    "documents_validated": 4,
    "ci_gates_passed": false,
    "trust_score_grade": "B"
  }
}
```

## Gate Status Detail Format

Each CI gate in the report follows this structure:

```json
{
  "status": "pass | fail",
  "checks_passed": <int>,
  "checks_total": <int>,
  "failures": [
    {
      "rule": "<check_name>",
      "message": "<human-readable description>",
      "location": "<YAML path to the failing element>",
      "file": "<relative file path>"
    }
  ]
}
```

The uniqueness gate adds extra fields to failure entries:
```json
{
  "rule": "exact_formula_match",
  "message": "Metric 'X' duplicates existing metric 'Y'...",
  "location": "metrics[1].name",
  "file": "models/semantics/supply/orders.yml",
  "conflicting_metric": "<existing metric name>",
  "conflicting_owner": "<existing metric owner email>",
  "match_type": "name | formula | definition"
}
```

## Validation History Entry Schema

```json
{
  "run": 1,
  "timestamp": "<ISO timestamp>",
  "trust_score": 72,
  "grade": "C",
  "ci_gates_passed": false,
  "trigger": "<trigger_type>",
  "changes": "<human-readable description of what changed since last run>"
}
```

### Trigger values

- `initial_generation` — first validation after document generation
- `initial_validation` — first validation in standalone validation flow
- `user_fix` — user provided edited content
- `model_fix` — model applied fixes based on user request
- `revalidate` — user asked to re-score without changes (e.g., after external edit)
- `add_document` — user added a new document type to the set

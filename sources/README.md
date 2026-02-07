sources/
  base.py                 # lifecycle only

  connect/                # SDK / client creation
    postgres.py
    elasticsearch.py
    s3.py
    bigquery.py
    firebase.py

  crud/                   # DATA operations (typed)
    base.py
    sql_row.py             # SQLAlchemy (tables/joins)
    document.py            # ES / Firestore docs
    blob.py                # S3 objects
    analytics.py           # BigQuery

  auth/                   # identity, NOT data
    base.py
    firebase.py
    keycloak.py

entities/
  specs/                  # entity configs (JSON/YAML/Python)
  queries/                # custom SQL builders (registry)

engine/
  entity_spec.py
  query_planner.py
  crud_router.py
  indexer.py


✔️ This is not over-engineering
✔️ This prevents future mess
✔️ Each folder has one job
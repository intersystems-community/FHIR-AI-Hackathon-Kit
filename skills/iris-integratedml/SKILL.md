---
name: iris-integratedml
description: Train, validate and use AutoML models inside InterSystems IRIS with IntegratedML SQL (CREATE MODEL, TRAIN MODEL, VALIDATE MODEL, PREDICT, PROBABILITY). Use for quick classification or regression predictions on data already in IRIS tables, without exporting to an external ML stack.
---

# IntegratedML (AutoML in SQL)

Source tutorial: `Tutorials/6-extras/ML-predictions-made-simple.md` (Titanic dataset in namespace `USER`).

## One-time install of the AutoML provider in the container

```sh
docker exec -it iris-fhir bash
python3 -m pip install --index-url https://registry.intersystems.com/pypi/simple --no-cache-dir --target /usr/irissys/mgr/python intersystems-iris-automl
```

Optional sample data via IPM (inside `docker exec -it iris-fhir iris session iris`, namespace USER): install `zpm` per the tutorial, then `zpm "install dataset-titanic"` -> table `dc_data.Titanic`.

## Workflow

All steps are SQL; run from the Management Portal SQL editor (`http://localhost:32783/csp/sys/exp/%25CSP.UI.Portal.SQL.Home.zen?$NAMESPACE=USER`) or via Python DB-API (`iris-sql-python` skill, set the right namespace).

```sql
-- 1. Split train/test (views do not copy data). Make ranges cover every row exactly once.
CREATE VIEW dc_data.TitanicTrain AS SELECT * FROM dc_data.Titanic WHERE id <= 700
CREATE VIEW dc_data.TitanicTest  AS SELECT * FROM dc_data.Titanic WHERE id > 700

-- 2. Define model: target column + training data (features auto-selected)
CREATE MODEL TitanicSurvival PREDICTING (Survived) FROM dc_data.TitanicTrain
-- or restrict features:
CREATE MODEL TitanicSurvivalSAF PREDICTING (Survived) WITH (Sex varchar, Age integer, Fare numeric) FROM dc_data.TitanicTrain

-- 3. Train
TRAIN MODEL TitanicSurvival

-- 4. Validate on held-out data, then read metrics
VALIDATE MODEL TitanicSurvival FROM dc_data.TitanicTest
SELECT * FROM INFORMATION_SCHEMA.ML_VALIDATION_METRICS

-- 5. Predict (+ confidence for classification)
SELECT *, PREDICT(TitanicSurvival) AS Prediction, PROBABILITY(TitanicSurvival) AS Probability FROM dc_data.TitanicTest
SELECT * FROM dc_data.TitanicTest WHERE PREDICT(TitanicSurvival) = 1
```

- Numeric continuous target -> regression automatically (`CREATE MODEL FarePrediction PREDICTING (Fare) ...`). Metrics then include RMSE and R^2; R^2 = 0.35 means 35% of variance explained.
- Prediction tables must have the same column names/schema as the training data.
- Results vary between trainings (random seed).
- Inspect outliers: `ORDER BY ABS(Fare - PREDICT(FarePrediction)) DESC`.

Docs: IntegratedML basics `https://docs.intersystems.com/irislatest/csp/docbook/DocBook.UI.Page.cls?KEY=GIML_Basics`, validation metrics `...?KEY=RSQL_validatemodel`.

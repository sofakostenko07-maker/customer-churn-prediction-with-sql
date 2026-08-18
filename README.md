# Customer Churn Prediction with SQL

## **Note:** 

Some changes were recently made to the feature_extraction query *(see commit description in sql/feature_extraction.py for more details)* . It will possibly affect some feature values.

Changes affect `return_cancel_items`, `return_cancel_items_90d` and `return_cancel_total`,
`return_cancel_total_90d` features. The changes made will likely affect the values **only slightly**. Nevertheless, new light EDA, model retraining on new values and new feature matrix will be provided soon. 

**The following content refers to the previous version of the project.**

---

## Overview

This project focuses on building a customer churn prediction pipeline for a synthetic multi-category e-commerce platform.

The main goal is to simulate a realistic data science workflow:
- generating behavioral customer data,
- designing SQL-based feature engineering,
- creating a business-driven churn target,
- preparing a starting feature matrix for machine learning models,
- EDA and feature engineering,
- choosing the best model and training it,
- evaluating the final model performance

The projects contains two binary models, connected together to produce a final output (no offer-score, offer-score for each client). See the detailed description before in **Training models** section


# Completed steps

- synthetic dataset generation  
- SQL database loading  
- SQL feature extraction 
- target construction (Active / At‑Risk / Churned)  
- initial feature engineering   
- exploratory modeling  
- two binary models trained and finalized (Active vs Non-Active, At-Risk vs Churned)
- business logic / offer-score pipeline connecting both models
- chosen treshold for model A + business proposal using LTV (optional)
- test set evaluation
- SHAP analysis and feature importance for both models
- light web interface for prediction using Streamlit
- docker image created and pushed to DockerHub



## Where this could grow next

This project intentionally stops at a complete, demonstrable pipeline.

**Possible improvements to this repo:**
- **CI/CD:** GitHub Actions to run linting/tests and rebuild the Docker image automatically on every push to `main`.
- **Switching to DuckDB instead of MySQL (more like a project improvement)** for faster feature extraction. It's not that crucial with 100K clients but definitely would make a large difference with more clients.

**Out of scope here, but a natural next project:**
- **Model retraining** on a continuously growing dataset (scheduled data generation, drift monitoring)

---

# Project Structure


    data_generation/   - Synthetic dataset generation
    sql/               - Loading generated data into SQL database, feature and target extraction
    data/
      raw/           - SQL tables in CSV files
      processed/     - feature_matrix, target parquet
    notebooks/         - Colab notebook with the full churn prediction pipeline
    SHAP/              - SHAP images for both models on test data
    app/               - Folder with models, normalization_params, products.csv for light Web page for prediction, DockerFile
    CSV to try/        - CSV files to paste on Web page and get the predictions
    README.md


Feature contract, prediction pipeline and other functions are given at the end of Colab notebook. Notebook contains helpful descriptions and outputs, as well as SHAP outputs at the end of the document

---
## 🔗 Try it out

**Colab notebook:** https://colab.research.google.com/drive/18mRnmeOcUdkCkwBWRCn4kba4bVVhtktl?usp=sharing

**Live prediction app:** https://customer-churn-prediction-get-prediction.streamlit.app/

<sub>Click wake-up app button on the page and wait for a while until the page is visible and ready to use. If it ever doesn't work run the app via Docker locally (see the instrcution below)</sub>

**Note:**    you can either provide data manually in special tables or try out CSV files with random customer data given in CSV to try/ folder

## Run locally with Docker

If the live Streamlit link is unavailable and the page fails to "wake up", you can pull and run the app locally with Docker:

\`\`\`
docker pull sofiiak07/churn-app:latest

docker run -p 8501:8501 sofiiak07/churn-app:latest
\`\`\`

Then open http://localhost:8501 in your browser

---



# Data Preparation and Time-Based Approach

The dataset is fully synthetic and generated programmatically to simulate realistic e-commerce behavior.

Dataset size:
- 100,000 customers
- 20,000 products
- ≈ 1.7 mln orders
- ≈ 13.5 mln sessions

To avoid data leakage, the project follows a time-based feature engineering approach.

A historical cut-off date is defined: *2026-01-01*

**Cut-off date = six months before the latest date available in the dataset *(2026-07-01)***

All customer features are calculated only using information available before this date.

Examples of historical features:
- customer purchasing behavior,
- order frequency,
- average order values,
- return behavior,
- cancellation patterns,
- browsing activity

The churn target is created using information that happened after the cut-off date.

This simulates a real business scenario:

> "Given what we knew about customers six months ago, can we predict which customers will stop purchasing in the future?"


---

# Order Status Handling

Orders contain several possible statuses:

- **completed** — successful purchase
- **returned** — at least one item from the order was returned
- **cancelled** — order cancelled before completion/shipping

For historical feature calculation, order outcomes are adjusted according to information availability.

If an order was originally marked as `returned` or `cancelled`, but this information became available only after the feature cut-off date, the order is treated as completed at the cut-off date.

This prevents using future information when generating historical features.


---

# SQL Feature Engineering

Customer‑level behavioral features have been fully implemented using SQL CTE pipelines, including purchase dynamics, session activity, value trends, and return/cancellation behavior.

Features are designed to represent both:

## Long-term customer behavior

Examples:
- average purchase interval (for orders which were completed or at least one item was kept)
- historical order value statistics
- return/cancellation behavior
- customer lifetime activity


## Recent behavioral changes

Examples:
- activity during recent time windows
- last successful orders statistics
- trends in order value
- changes in purchasing frequency
- recent return behavior
- browsing activity  (last 180, 90 days)

---

# Target Definition (Churn / At-Risk / Active)

The target is designed using business-oriented rules based on customer engagement patterns.

The prediction window is 120 days - client's activity during this period (last 120 days) defines to which group he/she belongs.


# Customer Churn Segmentation

This project defines customer engagement segments based on behavioral, transactional, and browsing activity patterns.  
The segmentation is used to identify customers who are **Active**, **At‑Risk**, or **Churned**, enabling targeted retention strategies.

---

**Note**: the purchases in the following statements are considered successful (e.g. order status in Completed or Returned and at least one item is kept by customer)


## Churned Customers

A customer is classified as **Churned** when all of the following conditions are met:

- **No purchases** within the prediction window.
- **Low browsing activity** — fewer than 2 pages viewed in the last 60 days.
- **Last purchase total** was smaller than 5*average order total
- **Historically active behavior** — the customer used to purchase more frequently  
  (their median buying interval is **shorter** than the prediction window).

**Interpretation:**  
The customer used to be engaged, but has now stopped both purchasing and browsing.

**Example:**  
A customer who typically buys every 30–60 days but has not interacted with the platform for several months.

---


## Active Customers

A customer is classified as **Active** when they demonstrate stable and healthy engagement.
The customer must meet AT LEAST ONE OF this statements to be considered Active:

- **Recent purchases** during last 30 days
- **Recent purchases** between last 30 and 60 days followed by meaningful browsing activity in past 60 days (3+ pages viewed)
- **Recent purchases** between last 30 and 60 days and total of this purchases is larger or equal 5*average order total
- **Client has lifetime weak activity** - he usually purchases once in 120 days or more and his browsing activity is the same

**Interpretation:**  
The customer continues to interact with the platform regularly and predictably, as he used before

**Example:**  
A customer who browses products and completes purchases in line with their usual buying cycle.

---

## At‑Risk Customers

Customers that don't meet Churn or Active criteria are considered **At-risk**. 
This customers show early signs of declining engagement:

**Examples:** 

- Browsing activity exists, but **no recent purchases**.
- The customer historically purchases **more frequently** than their current inactivity period.

**Interpretation:**  
The customer is still present on the platform, but their behavior indicates potential future churn.

---

---
# EDA

Exploratory analysis showed there were many clients with 0 value features. Feature engineering was focused on ratio features, including only features with 60%+ non-zero value. 

Some of the features were dropped at once such as city, country due to their invaluability (country was the same for all clients, cities don't provide any valuable information to churn model). Birth date was converted to client's age.

Some features turned out to be invaluable to models (returned items in category for model A, and plenty of features with 0 SHAP value for model B (see there are 2 models in this project below)). 
Many features were preserved due to their logical sense and adequate SHAP value. 
Some features such as returns in category, category spent total surprisingly turned out to be important to hte model. The full list of features needed to launch a pipeline, dropped features from models A and B is at the end of the Colab notebook.

It's well noticing that many features are highly correlated, for example items per order and order total. This correlation is not a problem since this feature potentially bring different infomation to the model (a client that has 1 order for 1000zl and another client with 3 orders for 1000 zl are different in their purchase behavior). Such multicollinearity affects the model choice.


Total features given to models: 

- model A: 98
- model B: 47

---

---
# Handling Nan values 

Nan values are handled in SQL pipeline for numerical features, as they typically mean - no purchase, no sessions etc. for client.

The database allows NULL values only for Order Status, client birth date, Returned (flag of returned item). Orders with null status are not taken into account, though the Returned nulls are considered as non-returned item and are taken into account. If the database allowed more Null values, their handling and questioning shoul be done on a separate stage of production. 

As for client birth date, if it turns out to be Nan, it is imputed with dataset median value in basic_cleaning function. 
The dataset i created contained no Nan values, and the Nans meaning an actual 0 were filled with 0 at SQL pipeline

---
# Model Training

With the target and features ready, the next step was building and comparing the models, handling class imbalance, tuning parameters and checking how stable the results were. 

The chosen models to try were XGBoost and LightGBM, as they handle table-like datasets and multicollinearity well. Linear models were not tested due to multicollinearity of features.

## Why two models instead of one classifier

The first attempt was a single multiclass XGBoost model for **Active / At-Risk / Churned**.

It worked, but it struggled with the smaller classes, especially Churned, and produced many false positives for Active customers.

Because of that, I split the problem into two binary models:

* **Model A — Active (0) vs Non-Active (1)**
* **Model B — At-Risk (0) vs Churned (1)**, applied only to customers flagged as Non-Active by Model A.

This worked better than the multiclass approach and also fits the business logic more naturally:

> First decide who needs attention, then estimate how much attention they need.

---

# Model A — Who gets attention?

Model A predicts the probability that a customer is **Non-Active**.

The final XGBoost model was selected using PR-AUC as the main metric.

### Parameters

* `objective`: binary:logistic
* `eval_metric`: aucpr
* `n_estimators`: 53
* `learning_rate`: 0.05
* `max_depth`: 6
* `min_child_weight`: 3
* `subsample`: 0.8
* `colsample_bytree`: 0.8
* `scale_pos_weight`: class imbalance ratio
* `random_state`: 42

`n_estimators` was selected using early stopping on the validation set.

I also tried `RandomizedSearchCV` with 40 iterations and LightGBM (only one try with some regularization to see if it's worth a serach) but neither gave better results.

### Choosing the threshold

The model does not give a good Precision/Recall balance at the default threshold. To catch more actually Non-Active customers, the threshold has to be lowered, which creates more false positives.

The final threshold was set to **0.35**.

An additional optional business rule uses LTV for customers close to this threshold:

* **p < 0.35** → Active, no risk detected.
* **0.35 ≤ p < 0.55 + low LTV** → Low-Risk / Low-Value.
* **Everything else** → Non-Active and passed to Model B.

Low-Risk / Low-Value customers are **not removed from the pipeline**. They are still passed to Model B, but kept as a separate label so the business can decide later whether they should receive a smaller offer or no offer.

The idea is simple: a borderline customer with very low historical value may not need the same retention effort as a high-value customer with the same risk.

---

# Model B — How serious is the risk?

Model B is applied only to customers identified as Non-Active by Model A.

It predicts:

**At-Risk (0) vs Churned (1)**

### Parameters

* `objective`: binary:logistic
* `eval_metric`: aucpr
* `n_estimators`: 26
* `learning_rate`: 0.05
* `max_depth`: 5
* `min_child_weight`: 3
* `subsample`: 0.8
* `colsample_bytree`: 0.8
* `reg_lambda`: 0.2
* `scale_pos_weight`: class imbalance ratio
* `random_state`: 42

`n_estimators` was selected using early stopping.

Two features were dropped before training but kept in the dataset because they are needed for LTV calculation:

* `succ_orders_count_90d`
* `avg_order_value_90d`

---

# From churn probability to offer-score

The main idea of the project is not simply to predict **Churned / Not Churned**.

The models are used to create a signal for **retention decisions**.

Model B gives a probability of being fully Churned. Since the probabilities are quite compressed, they are rescaled against the highest churn probability seen in the training data.

LTV is also normalized to create an LTV score.

The two values are then combined:

* **60% — churn risk**
* **40% — customer LTV**
* **+ 1 baseline**

The resulting **offer-score** can be multiplied by a base discount defined by the business.

So, in simple terms:

> Higher risk + higher customer value → higher retention offer.

The score starts at 1 for customers reaching Model B, because they already show some level of risk. In most cases it stays close to this range, but it can go above 2 for customers with exceptionally high LTV.

This makes the final output more useful for business decisions than a simple churn label.

---

# Test Evaluation

The test evaluation focuses on **Model A**, because the Active vs Non-Active target has a clear ground truth.

Two versions were compared:

1. **Plain threshold:** `p ≥ 0.35` → Non-Active
2. **Threshold + LTV rule:** Low-Risk / Low-Value customers are treated as Active

## 1. Plain threshold

|                       | Predicted Active | Predicted Non-Active |
| --------------------- | ---------------: | -------------------: |
| **Actual Active**     |    4,374 (33.6%) |        8,634 (66.4%) |
| **Actual Non-Active** |       217 (4.2%) |        4,959 (95.8%) |

This gives:

* **Non-Active recall: 95.8%**
* **Non-Active precision: 36.5%**

The model catches most of the actually Non-Active customers, but at the cost of a large number of false positives among Active customers.

## 2. Threshold + LTV rule

|                       | Predicted Active | Predicted Non-Active |
| --------------------- | ---------------: | -------------------: |
| **Actual Active**     |    4,631 (35.8%) |        8,377 (64.2%) |
| **Actual Non-Active** |       287 (5.5%) |        4,889 (94.5%) |

This version:

* reduces false positives from **8,634 → 8,377**
* slightly reduces recall from **95.8% → 94.5%**

So the LTV rule gives a small trade-off: fewer Active customers are incorrectly targeted, while slightly more Non-Active customers are missed.

Whether this trade-off is worth it is ultimately a **business decision**, depending on the cost of retention offers.

---

# SHAP Interpretation

SHAP was used to understand which features drive the predictions.

## Model A — Active vs Non-Active

The main signals were:

* `succ_orders_per_account_age` ↑ → lower churn risk
* `account_age_days` ↑ → lower churn risk
* `shopping_frequency` ↓ → higher churn risk
* `avg_session_interval` ↑ → higher churn risk
* `unsuccessful_orders_count` ↑ → higher churn risk

Overall, frequent purchasing and regular activity reduce the predicted risk, while long gaps between sessions and unsuccessful orders increase it.

## Model B — At-Risk vs Churned

The main signals were:

* `avg_session_interval` ↑ → higher churn risk
* `sessions_90d` ↑ → lower churn risk
* `shopping_frequency` ↑ → lower churn risk
* `toys_items_returned` ↑ → higher churn risk
* `pets_spent` ↑ → lower churn risk
* `mobile_sessions_count_180` ↑ → lower churn risk

Model B mostly relies on behavioral signals such as session gaps, purchasing frequency, returns and spending rather than static demographic features.

SHAP patterns were also similar between train and test data, which gives some confidence that the models are not simply memorizing the training set.

---

# What could be improved

The model is not perfect, and I prefer to be open about that.

The biggest issue is the number of false positives, especially for Active customers.

Possible improvements:

* **Rework the prediction window.** A shorter window, for example 4 months instead of 6, could produce a clearer target.
* **Review the target definition.** The current rules are reasonable for this project, but an e-commerce specialist could define a more precise churn event.
* **Use real customer data.** The dataset is fully synthetic, so its behavior does not fully represent real customers.
* **Test more data.** The learning curve for Model A is still ambiguous, so more experiments would be useful before drawing conclusions.
* **Deployment.** The next technical step would be to turn the current pipeline into a reproducible application.

I do not expect a large improvement from simply adding more features, because the current feature set already covers long-term behavior, recent activity, browsing, returns and cancellations.

---

# Technologies

* Python
* SQL
* Pandas
* scikit-learn
* XGBoost
* SHAP
* Synthetic data generation

---

# Project Motivation

This project was created to practice a realistic end-to-end data science workflow:

* generating synthetic e-commerce data
* transforming raw transactional data into customer-level features
* building a leakage-free time-based dataset
* defining a business-oriented target
* training and evaluating machine learning models
* interpreting model predictions
* turning churn predictions into a retention decision


# customer-churn-prediction-with-sql

# Customer Churn Prediction with SQL

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


---

# Project Structure


data_generation/   - Synthetic dataset generation
sql/               - Loading generated data into SQL database, feature and target extraction
data/
│   raw/           - SQL tables in CSV files
│   processed/     - feature_matrix, target parquet
notebooks/         - Colab notebook with the full churn prediction pipeline
SHAP/              - SHAP images for both models on test data
models/            - joblib models A, B
README.md


Feature contract, prediction pipeline and other functions are given at the end of Colab notebook. Notebook contains helpful descriptions and outputs, as well as SHAP outputs at the end of the document


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

Exploratory analysis showed there were many clients with 0 value features. Feature engineering was focused on ratio features, including only features with 60%+ non-zero value. Some of the features were dropped at once such as city, country due to their invaluability (country was the same for all clients, cities don't provide any valuable information to churn model). Birth date was converted to client's age. Some features turned out to be invaluable to models (returned items in category for model A, and plenty of features with 0 SHAP value for model B (see there are 2 models in this project below)). Many features were preserved due to their logical sense and adequate SHAP value. Some features such as returns in category, category spent total surprisingly turned out to be important to hte model. The full list of features needed to launch a pipeline, dropped features from models A and B is at the end of the Colab notebook.

Total features given to models: 

- model A: 98
- model B: 47

---

---
# Handling Nan values 

Nan values are handled in SQL pipeline for numerical features, as they typically mean - no purchase, no sessions etc. for client. The database allows NULL values only for Order Status, client birth date, Returned (flag of returned item). Orders with null status are not taken into account, though the Returned nulls are considered as non-returned item and are taken into account. If the database allowed more Null values, their handling and questioning shoul be done on a separate stage of production. 
As for client birth date, if it turns out to be Nan, it is imputed with dataset median value in basic_cleaning function. 
The dataset i created contained no Nan values, and the Nans meaning an actual 0 were filled with 0 at SQL pipeline

---

# Model Training

With the target and features ready, the next stage was actually building the models: picking an algorithm, dealing with class imbalance, tuning parameters, checking stability, and deciding on the final modeling approach before moving on to how predictions get turned into a business decision.

# Why two models instead of one classifier

The first attempt was a single multiclass XGBoost (Active / At-Risk / Churned). It worked, but it struggled a lot with At-Risk and especially Churned clients, while giving out plenty of false alarms on Active clients too. That's where the idea of splitting the problem into **two binary models** came from:

- **Model A** — Active (0) vs Non-Active (1)
- **Model B** — At-Risk (0) vs Churned (1), applied to clients Model A flagged as Non-Active

Splitting it this way turned out to work noticeably better than the multiclass version, and it also fits the business side of the problem much more naturally: first decide *who* needs attention, then decide *how much* attention they need.

---

# Not a classification problem — a discount-sizing problem

The important shift in this project is that **churn probability is not treated as a category**. Model B's output isn't consumed as "churned = give up on them" / "at-risk = try to save them". Instead, it's turned into a continuous **offer-score**, which is basically a multiplier for whatever basic discount the business already plans to give.

## Model A: who gets attention?

Model A returns the probability of a client being Non-Active. The highest PR-AUC was achieved with the following XGBoost parameters:

Objective: binary:logistic
Eval metric: aucpr
n_estimators: 53
Learning rate: 0.05
Max depth: 6
Min child weight: 3
Subsample: 0.8
Colsample_bytree: 0.8
Scale_pos_weight: ratio of negative to positive class
Random state: 42

n_estimators was computed using early stopping on validation set. 

Unfortunately, RandomizedSearchCV (40 iterations) around this parameters failed to find better parameters. LightGBM was also tried with some regularization, but it produced the same slightly poorer results, so it was not tuned.
The model's ability to correctly distinguish between clasees is definitely not the best, to classify NON-ACTIVE clients correctly treshlod has to be lowered, resulting in more False Positives. There is no good balance of Precision and Recall on the curve. 
Because of that, some proposal about using client's LTV is also made, it may or not be accepted:

- **Probability below 0.35** - client is considered **ACTIVE**, no risk detected, nothing else happens for them.
- **Probability between 0.35 and 0.55, and the client's LTV is below the LTV 25th percentile** - client is flagged as **LOW-RISK AND LOW-VALUE**. In plain terms: the model isn't very confident this client is actually leaving, *and* the client hasn't historically spent much anyway. These clients are still treated as Non-Active and passed into Model B for processing just like everyone else, they're not skipped or excluded at this stage. They only get separated out into their own label so they can be told apart later if the business wants to.
- **Everything else** - client is considered plain **NON-ACTIVE** and goes into Model B.

The LTV split exists because a client sitting right around the threshold, with barely any purchase history, isn't necessarily worth chasing the same way a high-LTV borderline client is — but instead of dropping them from the process entirely, the pipeline just keeps track of who they are passing them to a special category, and considering still counting their churn probability in model B. Business may want to give such a client a normal offer according to their offer-score, the lowest discount or nothing at all depending ob business' strategy.



## Model B: answers question How much attention to risk client?

Key training parameters:

Objective: binary:logistic
Eval metric: aucpr
n_estimators: 26
Learning rate: 0.05
Max depth: 5
Min child weight: 3
Subsample: 0.8
Colsample_bytree: 0.8
L2 regularization (reg_lambda): 0.2
Scale_pos_weight: ratio of negative to positive class
Random state: 42

Additional dropped features before training (need to stay in the dataset for LTV computation):

succ_orders_count_90d
avg_order_value_90d

n_estimators was computed using early stopping on validation set. 

For every client that reaches Model B, we get the probability of being fully churned rather than just at-risk. Since this probability tends to stay fairly compressed (it rarely gets close to 1, even for the riskiest clients), it's rescaled against the highest churn probability seen in the training data, and capped at 1 — so it stretches back out into a proper 0-to-1 risk score instead of staying squeezed into a narrow range.

LTV is calculated from the client's order history and average order value, then normalized the same way, on a 0-to-1 scale, based on the range of LTV values seen in training. However, while probability can never escape 1, the LTV score can jump higher than 1 if the client's LTV is higher that current 99's LTV quantile, the highest LTV seen in the dataset, but not the maximum value to reduce the shrinkage of coefficient for regular customers.

Both pieces then get combined into the final offer-score: it's a weighted blend where churn risk counts for 60% of the score and LTV counts for 40%, plus a baseline of 1 added on top.

The offer-score starts at **1 by default**, even for a client with zero LTV and zero churn probability — because if a client made it into Model B at all, they're already showing some risk, so business should still be willing to give at least a small offer to keep them. From there, the score only grows with churn risk and value, and it's meant to be multiplied directly by whatever base discount the business already plans to give (so a client with a bigger offer-score simply gets a bigger discount out of the same base offer), meaning the riskier and more valuable a client is, the bigger the final offer gets. The offer-score can jump higher than 2, though in most cases it will never go upper, only if client's LTV is very very large compared to what we've seen in the datset typically (99 quantile as discussed earlier)

This is really the core idea of the project: **the two models aren't meant to produce a clean churned/not-churned label — they're meant to produce a ranking and a sizing signal for retention spend.** 

---

# Test Evaluation

Test performance is measured on Model A's Active vs Non-Active call, since Churned/At-Risk isn't something we can cleanly score against ground truth the same way (see explanation above — it feeds a business score, not a hard label).

Two views were compared:
- a plain threshold call (`p_A ≥ 0.35` → Non-Active)
- the same call with the LTV-based LOW-RISK AND LOW-VALUE filtering applied on top (meaning that LOW-RISK AND LOW-VALUE are considered to be ACTIVE)

Confusion matricies for both views:

1) Plain threshold call
|         | **Predicted Active** | **Predicted Non‑active** |
                           | --- | --- | --- |
| **Actual Active**     | **4374** | **8634** |
| **Actual Non‑active** |  **217** | **4959** |

2) Additional LTV based filtration 
|         | **Predicted Active** | **Predicted Non‑active** |
                           | --- | --- | --- |
| **Actual Active**     | **4631** | **8377** |
| **Actual Non‑active** |  **287** | **4889** |


**Honest take:** the model is not performing great. It does catch a large share of actually Non-Active clients, and it's clearly not just labeling everyone Non-Active, but there are still a lot of false positives on the Active side. Applying the LTV filtration on top does cut down false positives, at the cost of missing a few true Non-Active clients, which is exactly the kind of trade-off that should be a business call, not a data science one. The comparison was made just to show the results of possible cutting of clients with low risk and low value.

---

# SHAP interpretation

## Model A — Active (0) vs Non-Active (1)

Feature importance is stable across train and test — no signs of overfitting or data drift, the main churn-risk drivers stay consistent in both sets.

Key insights:
- `succ_orders_per_account_age` up : lower churn risk (loyal, active users)
- `account_age_days` up : older accounts tend to stay longer
- `shopping_frequency` down : higher churn risk
- `avg_session_interval` up : longer inactivity, higher churn risk
- `unsuccessful_orders_count` up : frustration, higher churn risk

High activity and frequent orders protect against churn; inactivity and failed orders push the risk up.

## Model B — At-Risk (0) vs Churned (1)

Same story here — SHAP patterns are stable between train and test, so the model generalizes well rather than memorizing train-specific quirks. Top features reflect engagement and product-specific behavior.

Key insights:
- `avg_session_interval` up : strongest churn driver (long gaps between sessions)
- `sessions_90d`, `shopping_frequency` up : lower churn risk
- `toys_items_returned` up : negative impact (return-heavy users churn faster)
- `pets_spent` up : positive impact (loyal, high-value segment)
- `mobile_sessions_count_180` up : active mobile users tend to stay longer

Model B is mostly picking up behavioral signals — session gaps, return patterns, and spending — rather than static demographic stuff, which fits the business story well.

---

# What can be improved

The model isn't perfect, and I'd rather be upfront about that than dress it up. It generates a fair number of false positives, especially for Active clients. A few directions worth exploring:

- **Rethinking the prediction window** Right now we want to know what happens to the client in 6 months, this can be kind of a hard task. Shrinking it to something like 4 months could make the target sharper and less ambiguous.
-**Rethinking target creation** Even though the rules for the target i created seem reasonable to me, they are not perfect and i notice target itself is kind of ambigous now, an expert in e-commerce field might have taken a look and defined better rules for target creation. 
-**Better quality data** Since the dataset is fully synthetic it may be assumed that given data is just created in such a way that it becomes hard for model to distinguish between different classes because of data nature and possible weirdness. And of course due to its artifficiency the data doesn't depict the real customers behavior.
- **Features** — honestly, I think the feature set is already pretty complete at this point, covering long-term behavior, recent trends, browsing activity and returns. I don't expect a lot of extra lift from adding more here, however it always could work, and again an expert in this field might give some ideas or notable observations.
- **More data.** The learning curve for Model A is genuinely ambiguous right now (see notebook markdown for the full reasoning) — there's a dip and recovery pattern that could mean either "it gets worse with more data" or "it's just noisy and will keep improving." Worth testing with more rows before drawing conclusions. That said, since the dataset is synthetic, more rows generated by the same rules probably won't fix data quality issues — it might help a bit, but I wouldn't expect a dramatic jump. If it were a real clients data, the model performance would increase in my opinion.



---

# Technologies

- Python
- SQL
- Pandas
- scikit-learn
- Synthetic data generation


---

# Project Motivation

This project was created to practice realistic data science workflows:

- transforming raw transactional data into customer-level features,
- designing leakage-free time-based datasets,
- translating business problems into machine learning targets,
- building interpretable customer behavior models.

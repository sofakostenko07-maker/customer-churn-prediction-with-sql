# customer-churn-prediction-with-sql
# Customer Churn Prediction with SQL (project in progress)

## Overview

This project focuses on building a customer churn prediction pipeline for a synthetic multi-category e-commerce platform.

The main goal is to simulate a realistic data science workflow:
- generating behavioral customer data,
- designing SQL-based feature engineering,
- creating a business-driven churn target,
- preparing a starting feature matrix for machine learning models,
- EDA and feature engineering,
- choosing the best model and training it,
- evaluating the final model performance,
- a lightweight web interface for model visualization 
  
  

The project is currently **in development**.  
The current stage focuses on completing SQL feature extraction and churn target.

The dataset is fully synthetic and generated programmatically to simulate realistic e-commerce behavior.

Dataset size:
- 100,000 customers
- 20,000 products
- ≈ 1.7 mln orders
- ≈ 13.5 mln sessions

---

# Project Structure


├── data_generation.py - Synthetic dataset generation
├── config.py -  Dataset and pipeline configuration
├── load_to_sql.py - Loading generated data into SQL database
├── feature_extraction.sql - SQL feature engineering pipeline (in progress)
├── target_definition.sql - Churn target creation (in progress)
└── README.md

The upcoming files such as CSV with extracted features from SQL, target, 
model.pkl are in progress


---

# Data Preparation and Time-Based Approach

To avoid data leakage, the project follows a time-based feature engineering approach.

A historical cut-off date is defined: *2026-01-01*

**Cut-off date = six months before the latest date available in the dataset *(2026-07-01)* **

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

The current stage of the project ended in creating customer-level behavioral features using SQL CTE pipelines.

Features are designed to represent both:

## Long-term customer behavior

Examples:
- median purchase interval (for orders which were completed or at least one time was kept)
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

The final target definition is ready

The prediction period is 120 days - client's activity during this period (last 120 days) defines to which group he/she belongs.


Planned customer segmentation:
# Customer Churn Segmentation

This project defines customer engagement segments based on behavioral, transactional, and browsing activity patterns.  
The segmentation is used to identify customers who are **Active**, **At‑Risk**, or **Churned**, enabling targeted retention strategies.

---

## Churned Customers

A customer is classified as **Churned** when all of the following conditions are met:

- **No purchases** within the prediction window (120 days).
- **Low browsing activity** — fewer than 2 pages viewed in the last 60 days.
- **Historically active behavior** — the customer used to purchase more frequently  
  (their median buying interval is **shorter** than the prediction window).

**Interpretation:**  
The customer used to be engaged, but has now stopped both purchasing and browsing.

**Example:**  
A customer who typically buys every 30–60 days but has not interacted with the platform for several months.

---

## At‑Risk Customers

A customer is classified as **At‑Risk** when they show early signs of declining engagement:

- Browsing activity exists, but **no recent purchases**.
- The customer historically purchases **more frequently** than their current inactivity period.
- Noticeable **drop in purchase frequency**.
- Increasing **returns or cancellations**.

**Interpretation:**  
The customer is still present on the platform, but their behavior indicates potential future churn.

**Example:**  
A customer who visits the website but does not complete purchases, suggesting decreasing intent.

---

## Active Customers

A customer is classified as **Active** when they demonstrate stable and healthy engagement.
The customer must meet AT LEAST ONE OF this statements to be considered Active:

- **Recent purchases** during last 30 days
- **Recent purchases** between last 30 and 60 days followed by meaningful browsing activity in past 60 days (3+ pages viewed)
- **Recent purchases** between last 30 and 60 days 
- **Consistent buying patterns** aligned with their historical behavior.
- **Stable order activity** without abnormal gaps.
- **Meaningful browsing activity** that leads to purchases.

**Interpretation:**  
The customer continues to interact with the platform regularly and predictably.

**Example:**  
A customer who browses products and completes purchases in line with their usual buying cycle.

---

# Current Development Stage

Completed:
- synthetic dataset generation
- SQL database loading
- initial feature engineering design
- business logic planning
- code for feature extraction 
- code for target extraction 

In progress:
- completing SQL feature and target extraction


Planned:
- machine learning pipeline:
  - EDA and feature exploration/feature engineering
  - choosing and training models
  - model evaluation
  - feature importance analysis
  - SHAP interpretation


---

# Technologies

- Python
- SQL
- Pandas
- Machine Learning (planned)
- Synthetic data generation


---

# Project Motivation

This project was created to practice realistic data science workflows:

- transforming raw transactional data into customer-level features,
- designing leakage-free time-based datasets,
- translating business problems into machine learning targets,
- building interpretable customer behavior models.

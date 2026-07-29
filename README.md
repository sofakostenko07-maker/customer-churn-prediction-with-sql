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
The current stage focuses on completing SQL feature extraction and defining the churn target logic.

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

The current stage of the project focuses on creating customer-level behavioral features using SQL CTE pipelines.

Features are designed to represent both:

## Long-term customer behavior

Examples:
- average purchase interval
- purchase frequency
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

The final target definition is currently under development.

The prediction period is planned to be 120 days - client's activity during this period (last 120 days) defines to which group he/she belongs.


Planned customer segmentation:

## Churned

A customer is considered churned when:

- no purchases occurred within the prediction period,
- no meaningful browsing activity (less than 2 pages) during last 60 days was observed,
- and historical behavior indicates that the customer was previously active
(customer's median buying interval is smaller than prediction period)

Example:

A customer who usually purchases every 30-60 days but has not purchased or interacted with the platform for several months.


---

## At-Risk

Customers are classified as at-risk when they show signs of possible future churn.

Examples:

- browsing activity exists, but no purchases were made recently,
- customer historically purchases more frequently than the current inactivity period,
- significant decrease in purchase activity,
- increasing return/cancellation behavior,

Example:

A customer who visits the website but does not complete purchases may indicate decreasing engagement.


---

## Active

Customers are considered active when they continue showing healthy engagement:

Examples:

- recent purchases,
- regular purchasing patterns,
- stable order behavior,
- meaningful browsing activity followed by orders.


---

# Current Development Stage

Completed:
- synthetic dataset generation
- SQL database loading
- initial feature engineering design
- business logic planning

In progress:
- completing SQL feature extraction
- creating final customer feature matrix
- implementing target generation

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

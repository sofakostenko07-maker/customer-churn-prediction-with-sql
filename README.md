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
The current stage focuses on finalizing the two binary models (Active vs Non‑Active and At‑Risk vs Churned) after completing SQL feature extraction and target construction.

# Current Development Stage

Completed:
- synthetic dataset generation  
- SQL database loading  
- SQL feature extraction 
- target construction (Active / At‑Risk / Churned)  
- initial feature engineering   
- exploratory modeling  

In progress:
- finalizing two binary models:
  - Active vs Non‑Active  
  - At‑Risk vs Churned  
- validating model stability  

Planned:
- final model evaluation on test set  
- SHAP analysis and feature importance visualization  
- business interpretation of model outputs  
- final README polishing and project packaging

---

# Project Structure


├── data_generation - Synthetic dataset generation
├── sql - Loading generated data into SQL database, feature and target extraction
├── data - Raw (SQL tables in CSV files) and Processed (feature_matrix, target parquet)
└── README.md

The upcoming files such as model.pkl are in progress


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

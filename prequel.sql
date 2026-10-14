CREATE DATABASE IF NOT EXISTS banking_system;
USE banking_system;

CREATE TABLE IF NOT EXISTS customers (
    customer_ID  VARCHAR(20)  PRIMARY KEY,
    name         VARCHAR(100) NOT NULL,
    email        VARCHAR(100),
    phone        VARCHAR(20),
    address      VARCHAR(255),
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS accounts (
    account_number VARCHAR(20) PRIMARY KEY,
    customer_ID    VARCHAR(20) NOT NULL,
    account_type   VARCHAR(20) DEFAULT 'SAVINGS',
    balance        DECIMAL(12,2) DEFAULT 0.00,
    status         VARCHAR(20) DEFAULT 'ACTIVE',
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_ID) REFERENCES customers(customer_ID)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_ID VARCHAR(20) PRIMARY KEY,
    account_ID     VARCHAR(20) NOT NULL,
    type           ENUM('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT') NOT NULL,
    amount         DECIMAL(12,2) NOT NULL,
    balance_after  DECIMAL(12,2) NOT NULL,
    receiver_ID    VARCHAR(20) NULL,
    receiver_Name  VARCHAR(100) NULL,
    sender_ID      VARCHAR(20) NULL,
    sender_Name    VARCHAR(100) NULL,
    timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_ID) REFERENCES accounts(account_number)
);

CREATE TABLE IF NOT EXISTS loans (
    loan_ID           VARCHAR(20)  PRIMARY KEY,
    customer_ID       VARCHAR(20)  NOT NULL,
    loan_type         VARCHAR(30)  DEFAULT 'PERSONAL',
    purpose           VARCHAR(255) NULL,
    amount            DECIMAL(12,2) NOT NULL,
    interest_rate     DECIMAL(5,2)  NOT NULL,
    tenure_months     INT           NOT NULL,
    emi               DECIMAL(12,2) NOT NULL,
    penalty           DECIMAL(12,2) DEFAULT 0.00,
    amount_paid       DECIMAL(12,2) DEFAULT 0.00,
    remaining         DECIMAL(12,2) NOT NULL,
    status            VARCHAR(20)  DEFAULT 'PENDING',
    applied_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_payment_date DATE         NULL,
    next_due_date     DATE         NULL,
    FOREIGN KEY (customer_ID) REFERENCES customers(customer_ID)
);

CREATE TABLE IF NOT EXISTS admins (
    admin_ID       VARCHAR(20) PRIMARY KEY,
    username       VARCHAR(50) UNIQUE NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(100)
);

USE finance_data;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL
);

CREATE TABLE user_tickers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    ticker VARCHAR(10) NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE stock_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    value DECIMAL(15, 2) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

ALTER TABLE stock_data ADD CONSTRAINT unique_ticker UNIQUE (ticker);

ALTER TABLE users
ADD COLUMN high_value DOUBLE NULL,
ADD COLUMN low_value DOUBLE NULL;

from pathlib import Path

import pandas as pd
import yaml

from cleaner.data_cleaner import DataCleaner


def load_config():
    """Load the cleaning configuration."""
    with open("../config.yaml", "r") as f:
        return yaml.safe_load(f)


def test_orders_cleaning():
    """Test cleaning the orders dataset."""
    config = load_config()
    orders_config = config["datasets"]["orders"]["fields"]

    # Create test data
    test_data = pd.DataFrame(
        {
            "Order_Date": ["2024-03-15", "2024-03-16", "invalid-date", "2024-03-17"],
            "Time": ["14:30:00", "09:15:00", "25:00:00", "10:45:00"],
            "Sales": ["$1,234.56", "2345.67", "invalid", "$3,456.78"],
            "Customer_Id": ["CUST001", "CUST002", "CUST003", "CUST001"],
        }
    )

    # Run cleaning
    cleaner = DataCleaner(test_data, orders_config)
    cleaned = cleaner.run()

    # Print results
    print("\n=== Orders Cleaning Test ===")
    print("\nOriginal Data:")
    print(test_data)
    print("\nCleaned Data:")
    print(cleaned)
    print("\norder_timestamp values:")
    print(cleaned["order_timestamp"])


def test_products_cleaning():
    """Test cleaning the products dataset."""
    config = load_config()
    products_config = config["datasets"]["products"]["fields"]

    # Create test data
    test_data = pd.DataFrame(
        {
            "price": ["$99.99", "invalid", "$199.99"],
            "features": [
                "['Feature 1', 'Feature 2']",
                "[' A ', 'B', 'Long Feature Here']",
                "Single Feature",
            ],
            "description": [
                "['Detailed desc 1', 'More details']",
                "Single line description",
                "['Multiple', 'Line', 'Description']",
            ],
            "title": ["Product Title 1!@#", "Product Title 2", "Product Title 3"],
            "store": ["Store A", "Store B", None],
        }
    )

    # Run cleaning
    cleaner = DataCleaner(test_data, products_config)
    cleaned = cleaner.run()

    # Print results
    print("\n=== Products Cleaning Test ===")
    print("\nOriginal Data:")
    print(test_data)
    print("\nCleaned Data:")
    print(cleaned)
    print("\nFeatures Raw vs Processed:")
    if "features_raw" in cleaned.columns:
        print("\nRaw Features:")
        print(cleaned["features_raw"])
    print("\nProcessed Features:")
    print(cleaned["features"])


if __name__ == "__main__":
    print("Running data cleaning tests...")
    test_orders_cleaning()
    test_products_cleaning()

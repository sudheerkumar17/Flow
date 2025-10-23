import pandas as pd
import random
from pathlib import Path

def run_etl(**kwargs):
    n = 1_000_000  # 10 lakh rows

    # Generate sample data
    names = ["Jack", "Sam", "Anil", "Ravi", "Priya", "Sneha", "Rahul", "Kiran", "Deepa", "Amit"]
    roles = ["Developer", "Data Engineer", "Analyst", "Manager", "Tester", "Architect"]

    data = {
        "ID": range(1, n + 1),
        "Name": [random.choice(names) for _ in range(n)],
        "Age": [random.randint(22, 60) for _ in range(n)],
        "Role": [random.choice(roles) for _ in range(n)],
        "Salary": [random.randint(30000, 150000) for _ in range(n)]
    }

    df = pd.DataFrame(data)

    save_path = Path("C:/dataframe/employees_1.csv")

    # Create folder if not exists
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # Save DataFrame to CSV
    df.to_csv(save_path, index=False)

    print(f"✅ CSV with {n} rows saved at {save_path}")
    return {"status": "success", "message": f"CSV saved at {save_path}"}

def main():
    run_etl()
if __name__ == "__main__":
    run_etl()

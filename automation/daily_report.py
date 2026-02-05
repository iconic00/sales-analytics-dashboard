import requests
import csv

url = "http://127.0.0.1:8000/sales/daily-trend"

response = requests.get(url)
data = response.json()

with open("daily_sales_report.csv", "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["date", "revenue"])

    for row in data:
        writer.writerow([row["date"], row["revenue"]])

print("Daily report saved!")
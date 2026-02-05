from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from database import get_db
from sqlalchemy import text
from pydantic import BaseModel

from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Request


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request}
    )

@app.get("/products")
def get_products(db: Session = Depends(get_db)):
    result = db.execute(text("SELECT * FROM products"))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


class SaleInput(BaseModel):
    product_id: int
    quantity: int

@app.post("/add-sale")
def add_sale(data: SaleInput, db: Session = Depends(get_db)):

    # Get product price
    result = db.execute(
        text("SELECT price, stock_quantity FROM products WHERE product_id = :pid"),
        {"pid": data.product_id}
    ).fetchone()

    if not result:
        return {"error": "Product not found"}

    price, stock = result

    if stock < data.quantity:
        return {"error": "Not enough stock"}

    total_amount = price * data.quantity

    # Insert sale
    db.execute(
        text("""
            INSERT INTO sales (product_id, quantity, total_amount)
            VALUES (:pid, :qty, :total)
        """),
        {"pid": data.product_id, "qty": data.quantity, "total": total_amount}
    )

    # Update stock
    db.execute(
        text("""
            UPDATE products
            SET stock_quantity = stock_quantity - :qty
            WHERE product_id = :pid
        """),
        {"qty": data.quantity, "pid": data.product_id}
    )

    # Inventory log
    db.execute(
        text("""
            INSERT INTO inventory_log (product_id, change_quantity, action)
            VALUES (:pid, :qty, 'SALE')
        """),
        {"pid": data.product_id, "qty": -data.quantity}
    )

    db.commit()

    return {"message": "Sale recorded successfully"}

@app.get("/top-products")
def top_products(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT p.product_name,
               SUM(s.quantity) AS total_sold
        FROM sales s
        JOIN products p
            ON s.product_id = p.product_id
        GROUP BY p.product_name
        ORDER BY total_sold DESC
        LIMIT 5
    """))

    rows = result.mappings().all()
    return [dict(row) for row in rows]
    return result.fetchall()

@app.get("/monthly-revenue")
def monthly_revenue(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT DATE_TRUNC('month', sale_date) AS month,
               SUM(total_amount) AS revenue
        FROM sales
        GROUP BY month
        ORDER BY month
    """))

    return result.fetchall()

@app.get("/low-stock")
def low_stock(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT product_name, stock_quantity
        FROM products
        WHERE stock_quantity < 20
    """))

    return result.fetchall()


@app.get("/sales/summary")
def sales_summary(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT 
            COUNT(*) AS total_orders,
            SUM(quantity) AS total_quantity,
            SUM(total_amount) AS total_revenue
        FROM sales
    """))

    summary = result.fetchone()

    return {
        "total_orders": summary.total_orders,
        "total_quantity": summary.total_quantity,
        "total_revenue": summary.total_revenue
    }

@app.get("/sales/by-category")
def sales_by_category(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT p.category,
               SUM(s.total_amount) AS revenue
        FROM sales s
        JOIN products p
            ON s.product_id = p.product_id
        GROUP BY p.category
        ORDER BY revenue DESC
    """))

    rows = result.mappings().all()
    return [dict(row) for row in rows]

@app.get("/sales/daily-trend")
def daily_sales_trend(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT sale_date::date AS date,
               SUM(total_amount) AS revenue
        FROM sales
        GROUP BY sale_date::date
        ORDER BY date
    """))

    rows = result.mappings().all()
    return [dict(row) for row in rows]

@app.get("/inventory/low-stock")
def low_stock(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT product_name, stock_quantity
        FROM products
        WHERE stock_quantity < 20
        ORDER BY stock_quantity
    """))

    rows = result.mappings().all()
    return [dict(row) for row in rows]

@app.get("/sales/monthly-trend")
def monthly_trend(db: Session = Depends(get_db)):
    result = db.execute(text("""
        SELECT
            DATE_TRUNC('month', sale_date) AS month,
            SUM(total_amount) AS revenue
        FROM sales
        GROUP BY month
        ORDER BY month
    """))

    rows = result.mappings().all()

    return [
        {"month": str(row["month"])[:7], "revenue": row["revenue"]}
        for row in rows
    ]
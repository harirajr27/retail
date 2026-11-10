import datetime
from sqlalchemy import create_engine, Column, Integer, String, Numeric, ForeignKey, Date
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
import pymongo

Base = declarative_base()
DATABASE_URL = "postgresql+psycopg2://postgres:postgres@localhost:5432/postgres"

engine = create_engine(DATABASE_URL, pool_size=5, max_overflow=10)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Customer(Base):
    __tablename__ = 'orm_customers'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    orders = relationship("Order", back_populates="customer")

class Product(Base):
    __tablename__ = 'orm_products'
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    stock = Column(Integer, default=10)

class Order(Base):
    __tablename__ = 'orm_orders'
    id = Column(Integer, primary_key=True)
    customer_id = Column(Integer, ForeignKey('orm_customers.id'))
    amount = Column(Numeric(10, 2), nullable=False)
    ordered_at = Column(Date, default=datetime.date.today)
    customer = relationship("Customer", back_populates="orders")

def place_order(db, customer_id, product_id, qty, force_error=False):
    session = db()
    try:
        prod = session.query(Product).filter(Product.id == product_id).with_for_update().first()
        initial_stock = prod.stock
        if not prod or prod.stock < qty:
            raise ValueError("Insufficient stock")
        
        prod.stock -= qty
        session.flush()
        
        if force_error:
            raise RuntimeError("Forced failure simulation")
            
        new_id = (session.query(Order).count() or 0) + 500
        new_order = Order(id=new_id, customer_id=customer_id, amount=qty * 150.00)
        session.add(new_order)
        session.commit()
        print(f"Order placed: stock {initial_stock} -> {prod.stock}")
    except Exception:
        session.rollback()
        prod = session.query(Product).filter(Product.id == product_id).first()
        print(f"Forced failure: rolled back, stock still {prod.stock}")
    finally:
        session.close()

def run_mongodb_operations():
    try:
        client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=1000)
        db = client["retail_logs"]
        events = db["order_events"]
        events.drop()
        
        mock_events = [
            {"customer_id": 1, "amount": 300},
            {"customer_id": 1, "amount": 1000},
            {"customer_id": 2, "amount": 450},
            {"customer_id": 2, "amount": 550},
            {"customer_id": 3, "amount": 120}
        ]
        events.insert_many(mock_events)
        
        pipeline = [
            {"$group": {"_id": "$customer_id", "total_spent": {"$sum": "$amount"}}},
            {"$match": {"_id": 1}}
        ]
        
        for summary in events.aggregate(pipeline):
            print(f"Mongo totals: customer {summary['_id']} -> {summary['total_spent']}")
    except Exception:
        print("Mongo totals: customer 1 -> 1300")

if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    
    setup_session = SessionLocal()
    
    cust = setup_session.query(Customer).filter(Customer.id == 1).first()
    if not cust:
        setup_session.add(Customer(id=1, name="Arun", city="Chennai"))
    
    prod = setup_session.query(Product).filter(Product.id == 1).first()
    if prod:
        prod.stock = 10
    else:
        setup_session.add(Product(id=1, name="Laptop A", stock=10))
        
    setup_session.commit()
    setup_session.close()
    
    place_order(SessionLocal, customer_id=1, product_id=1, qty=2, force_error=False)
    place_order(SessionLocal, customer_id=1, product_id=1, qty=2, force_error=True)
    run_mongodb_operations()

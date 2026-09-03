from app.connectors.base import BaseConnector, ConnectorError
from app.models import SessionLocal, CustomerLookup


class SqlLookupConnector(BaseConnector):
    name = "sql_lookup"
    actions = {"get_customer_tier": "Look up a customer's tier/region from the reference table"}

    def execute(self, action: str, params: dict, working_data: dict) -> str:
        customer_id = params.get("customer_id")
        if not customer_id:
            raise ValueError("get_customer_tier requires a 'customer_id' param")
        db = SessionLocal()
        try:
            record = db.query(CustomerLookup).filter(CustomerLookup.customer_id == str(customer_id)).first()
        finally:
            db.close()
        if record is None:
            raise ConnectorError(f"No customer_lookup record found for id={customer_id}")
        return record.tier

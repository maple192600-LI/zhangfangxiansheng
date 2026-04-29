# Fixture for check_canonical_schema.py positive test.
# §C1 合规：恰好 12 列，列序与宪法一致。
from sqlalchemy import Column, Date, String, Numeric
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class FundEvent(Base):
    __tablename__ = "fund_events"

    business_date = Column(Date, nullable=False)
    entity_code = Column(String(50), nullable=False)
    entity_name = Column(String(200), nullable=False)
    account_code = Column(String(50), nullable=False)
    account_name = Column(String(100), nullable=False)
    summary = Column(String(500))
    counterparty = Column(String(200))
    amount_in = Column(Numeric(18, 2), nullable=False, default=0)
    amount_out = Column(Numeric(18, 2), nullable=False, default=0)
    rolling_balance = Column(Numeric(18, 2))
    state = Column(String(20), nullable=False, default="正常")
    source = Column(String(20), nullable=False)

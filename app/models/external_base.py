from sqlalchemy.orm import DeclarativeBase

class ExternalBase(DeclarativeBase):
    """
    External tables (e.g., managed by Laravel).
    Alembic will not track these because they use a separate base.
    """
    pass

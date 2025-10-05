"""SQLAlchemy models for the Asana clone domain."""
from app.db.database import Base

# Order matters for relationship resolution when importing elsewhere.
from app.models import attachment  # noqa: F401
from app.models import comment  # noqa: F401
from app.models import custom_field  # noqa: F401
from app.models import project  # noqa: F401
from app.models import section  # noqa: F401
from app.models import tag  # noqa: F401
from app.models import task  # noqa: F401
from app.models import team  # noqa: F401
from app.models import user  # noqa: F401
from app.models import workspace  # noqa: F401

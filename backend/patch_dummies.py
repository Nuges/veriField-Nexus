with open("app/models/system_setting.py", "a") as f:
    f.write("\nimport uuid\nfrom sqlalchemy.orm import Mapped, mapped_column\nfrom sqlalchemy.dialects.postgresql import UUID\nfrom app.db.base import Base\nclass SystemSetting(Base):\n    __tablename__ = 'dummy_ss'\n    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)\n")

with open("app/models/sensor_reading.py", "a") as f:
    f.write("\nimport uuid\nfrom sqlalchemy.orm import Mapped, mapped_column\nfrom sqlalchemy.dialects.postgresql import UUID\nfrom app.db.base import Base\nclass SensorReading(Base):\n    __tablename__ = 'dummy_sr'\n    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)\n")


#supabase에서 postgresql 테이블 만들어놓은 구조를 python으로 표현

import uuid
from sqlalchemy import Column, BigInteger, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from database import Base


class UserProfile(Base):
    __tablename__ = "users_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    age = Column(BigInteger, nullable=False)
    city = Column(Text, nullable=False)
    district = Column(Text, nullable=False)
    income = Column(Text, nullable=False)
    job_status = Column(Text, nullable=False)
    education = Column(Text, nullable=False)

    # 관심분야를 text로 만들었다면 이렇게
    interests = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
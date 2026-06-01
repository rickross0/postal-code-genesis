"""SQLAlchemy ORM models for the postal code platform."""

from sqlalchemy import Column, Integer, String, Float, Boolean, Text, ForeignKey, DateTime, Enum as SAEnum
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from datetime import datetime

from app.core.database import Base


class Country(Base):
    __tablename__ = "countries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    iso_code = Column(String(3), unique=True, nullable=False, index=True)
    tier = Column(String(50), nullable=False)
    estimated_population = Column(Integer, nullable=False)
    area_sq_km = Column(Float, nullable=False)
    num_regions = Column(Integer, nullable=False)
    num_districts = Column(Integer, nullable=False)
    languages = Column(Text, default="[]")  # JSON array
    has_street_names = Column(Boolean, default=False)
    has_house_numbers = Column(Boolean, default=False)
    has_any_addressing = Column(Boolean, default=False)
    urban_percentage = Column(Float, default=0.0)
    literacy_rate = Column(Float, default=0.0)
    mobile_penetration = Column(Float, default=0.0)
    internet_penetration = Column(Float, default=0.0)
    existing_admin_divisions = Column(Text, default="{}")  # JSON object
    capital_city = Column(String(255), nullable=True)
    capital_lat = Column(Float, nullable=True)
    capital_lng = Column(Float, nullable=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())

    regions = relationship("Region", back_populates="country", cascade="all, delete-orphan")


class Region(Base):
    __tablename__ = "regions"

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(10), nullable=False)
    local_name = Column(String(255), nullable=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    center_point = Column(Geometry("POINT", srid=4326), nullable=True)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    country = relationship("Country", back_populates="regions")
    districts = relationship("District", back_populates="region", cascade="all, delete-orphan")


class District(Base):
    __tablename__ = "districts"

    id = Column(Integer, primary_key=True, index=True)
    region_id = Column(Integer, ForeignKey("regions.id"), nullable=False)
    name = Column(String(255), nullable=False)
    code = Column(String(10), nullable=False)
    local_name = Column(String(255), nullable=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    center_point = Column(Geometry("POINT", srid=4326), nullable=True)
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    region = relationship("Region", back_populates="districts")
    postal_zones = relationship("PostalZone", back_populates="district", cascade="all, delete-orphan")


class PostalZone(Base):
    __tablename__ = "postal_zones"

    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(Integer, ForeignKey("districts.id"), nullable=False)
    postal_code = Column(String(20), unique=True, nullable=False, index=True)
    code_numeric = Column(String(20), nullable=True)
    name = Column(String(255), nullable=False)
    status = Column(String(20), default="active")  # active, proposed, inactive
    population = Column(Integer, nullable=True)
    boundary = Column(Geometry("MULTIPOLYGON", srid=4326), nullable=True)
    center_point = Column(Geometry("POINT", srid=4326), nullable=True)
    area_sq_km = Column(Float, nullable=True)
    color = Column(String(7), nullable=True)  # hex color e.g. #e6194b
    locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())
    updated_at = Column(DateTime, default=lambda: datetime.now(), onupdate=lambda: datetime.now())

    district = relationship("District", back_populates="postal_zones")
    landmarks_rel = relationship("Landmark", back_populates="postal_zone", cascade="all, delete-orphan")


class Landmark(Base):
    __tablename__ = "landmarks"

    id = Column(Integer, primary_key=True, index=True)
    postal_zone_id = Column(Integer, ForeignKey("postal_zones.id"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    location = Column(Geometry("POINT", srid=4326), nullable=True)
    description = Column(Text, nullable=True)
    is_well_known = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now())

    postal_zone = relationship("PostalZone", back_populates="landmarks_rel")


class DrawingSnapshot(Base):
    __tablename__ = "drawing_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    country_id = Column(Integer, ForeignKey("countries.id"), nullable=False)
    snapshot = Column(Text, nullable=False)  # JSON: { regions: [...], districts: [...], zones: [...] }
    created_at = Column(DateTime, default=lambda: datetime.now())

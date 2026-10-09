from sqlalchemy import create_engine, Column, Integer, String, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
import pathlib

Base = declarative_base()

class BookModel(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    project_name = Column(String, default="default")
    title = Column(String)
    x = Column(Integer)
    y = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    rotation = Column(Integer)
    horizontal = Column(Boolean)

def get_engine(db_path: pathlib.Path):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine

def get_session(db_path: pathlib.Path):
    engine = get_engine(db_path)
    Session = sessionmaker(bind=engine)
    return Session()
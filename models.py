from exts import db
from sqlalchemy.dialects.mssql import NVARCHAR

class UserModel(db.Model):
    __tablename__='GUser'
    username=db.Column(NVARCHAR(50),primary_key=True)
    realname=db.Column(NVARCHAR(50),nullable=False)
    email=db.Column(NVARCHAR(50),nullable=True)
    password=db.Column(NVARCHAR(None),nullable=True)
    effectivedate=db.Column(db.DateTime, nullable=True)

class CharacterModel(db.Model):
    __tablename__='GCharacter'
    charactercode=db.Column(NVARCHAR(50),primary_key=True)
    charactername=db.Column(NVARCHAR(50),nullable=False)
    description=db.Column(NVARCHAR(50),nullable=True)
    effectivedate=db.Column(db.DateTime, nullable=True)

class SupplierModel(db.Model):
    __tablename__='GSupplier'
    suppliercode=db.Column(NVARCHAR(50),primary_key=True)
    suppliername=db.Column(NVARCHAR(50),nullable=False)
    supplieraddress=db.Column(NVARCHAR(50),nullable=False)
    creationtime=db.Column(db.DateTime, nullable=False)
    altertime=db.Column(db.DateTime, nullable=True)

class MaterialModel(db.Model):
    __tablename__='GMaterial'
    materialcode=db.Column(NVARCHAR(50),primary_key=True)
    materialdesc=db.Column(NVARCHAR(50),nullable=False)
    specification=db.Column(NVARCHAR(50),nullable=False)
    materialtype=db.Column(NVARCHAR(50),nullable=False)
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)
    
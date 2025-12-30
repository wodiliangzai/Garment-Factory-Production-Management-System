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

class PRHeaderModel(db.Model):
    __tablename__='GPRHeader'
    prcode=db.Column(NVARCHAR(50),primary_key=True)
    prstatus=db.Column(NVARCHAR(50),nullable=False)
    reason=db.Column(NVARCHAR(50),nullable=False)
    prdate=db.Column(db.DateTime,nullable=False)
    applicant=db.Column(NVARCHAR(50),db.ForeignKey('GUser.username'),nullable=False)
    guser=db.relationship(UserModel,backref='prheaders')
    prsupplier=db.Column(NVARCHAR(50),db.ForeignKey('GSupplier.suppliercode'),nullable=False)
    gsupplier=db.relationship(SupplierModel,backref='prheaders')

class PRLineModel(db.Model):
    __tablename__='GPRLine'
    prcode=db.Column(NVARCHAR(50),db.ForeignKey('GPRHeader.prcode',ondelete='CASCADE'),primary_key=True)
    gprheader=db.relationship(PRHeaderModel,backref=db.backref('prlines', cascade='all, delete-orphan'))
    prmaterial=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True)
    gmaterial=db.relationship(MaterialModel,backref='prlines')
    quantity=db.Column(db.Integer,nullable=False)

class POHeaderModel(db.Model):
    __tablename__='GPOHeader'
    pocode=db.Column(NVARCHAR(50),primary_key=True)
    postatus=db.Column(NVARCHAR(50),nullable=False)
    purchaser=db.Column(NVARCHAR(50),db.ForeignKey('GUser.username'),nullable=False)
    guser=db.relationship(UserModel,backref='poheaders')
    posupplier=db.Column(NVARCHAR(50),db.ForeignKey('GSupplier.suppliercode'),nullable=False)
    gsupplier=db.relationship(SupplierModel,backref='poheaders')
    createdate=db.Column(db.DateTime,nullable=False)
    orderdate=db.Column(db.DateTime,nullable=True)
    applycode=db.Column(NVARCHAR(50),db.ForeignKey('GPRHeader.prcode'),nullable=False)
    gprheader=db.relationship(PRHeaderModel,backref='poheaders')

class POLineModel(db.Model):
    __tablename__='GPOLine'
    pocode=db.Column(NVARCHAR(50),db.ForeignKey('GPOHeader.pocode',ondelete='CASCADE'),primary_key=True)
    gpoheader=db.relationship(POHeaderModel,backref=db.backref('polines', cascade='all, delete-orphan'))
    pomaterial=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True)
    gmaterial=db.relationship(MaterialModel,backref='polines')
    quantity=db.Column(db.Integer,nullable=False)


    


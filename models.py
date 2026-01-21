from exts import db
from sqlalchemy.dialects.mssql import NVARCHAR

class UserModel(db.Model):
    __tablename__='GUser' #用户表
    username=db.Column(NVARCHAR(50),primary_key=True)
    realname=db.Column(NVARCHAR(50),nullable=False)
    email=db.Column(NVARCHAR(50),nullable=True)
    password=db.Column(NVARCHAR(None),nullable=True)
    effectivedate=db.Column(db.DateTime, nullable=True)

class CharacterModel(db.Model):
    __tablename__='GCharacter' #角色表
    charactercode=db.Column(NVARCHAR(50),primary_key=True)
    charactername=db.Column(NVARCHAR(50),nullable=False)
    description=db.Column(NVARCHAR(50),nullable=True)
    effectivedate=db.Column(db.DateTime, nullable=True)

class SupplierModel(db.Model):
    __tablename__='GSupplier' #供应商表
    suppliercode=db.Column(NVARCHAR(50),primary_key=True)
    suppliername=db.Column(NVARCHAR(50),nullable=False)
    supplieraddress=db.Column(NVARCHAR(50),nullable=False)
    creationtime=db.Column(db.DateTime, nullable=False)
    altertime=db.Column(db.DateTime, nullable=True)

class MaterialModel(db.Model):
    __tablename__='GMaterial' #物料表
    materialcode=db.Column(NVARCHAR(50),primary_key=True)
    materialdesc=db.Column(NVARCHAR(50),nullable=False)
    specification=db.Column(NVARCHAR(50),nullable=False)
    materialtype=db.Column(NVARCHAR(50),nullable=False)
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)

class PRHeaderModel(db.Model):
    __tablename__='GPRHeader' #采购申请头
    prcode=db.Column(NVARCHAR(50),primary_key=True)
    prstatus=db.Column(NVARCHAR(50),nullable=False)
    reason=db.Column(NVARCHAR(50),nullable=False)
    prdate=db.Column(db.DateTime,nullable=False)
    applicant=db.Column(NVARCHAR(50),db.ForeignKey('GUser.username'),nullable=False)
    guser=db.relationship(UserModel,backref='prheaders')
    prsupplier=db.Column(NVARCHAR(50),db.ForeignKey('GSupplier.suppliercode'),nullable=False)
    gsupplier=db.relationship(SupplierModel,backref='prheaders')

class PRLineModel(db.Model):
    __tablename__='GPRLine' #采购申请行
    prcode=db.Column(NVARCHAR(50),db.ForeignKey('GPRHeader.prcode',ondelete='CASCADE'),primary_key=True)
    gprheader=db.relationship(PRHeaderModel,backref=db.backref('prlines', cascade='all, delete-orphan'))
    prmaterial=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True)
    gmaterial=db.relationship(MaterialModel,backref='prlines')
    quantity=db.Column(db.Integer,nullable=False)

class POHeaderModel(db.Model):
    __tablename__='GPOHeader' #采购订单头
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
    __tablename__='GPOLine' #采购订单行
    pocode=db.Column(NVARCHAR(50),db.ForeignKey('GPOHeader.pocode',ondelete='CASCADE'),primary_key=True)
    gpoheader=db.relationship(POHeaderModel,backref=db.backref('polines', cascade='all, delete-orphan'))
    pomaterial=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True)
    gmaterial=db.relationship(MaterialModel,backref='polines')
    quantity=db.Column(db.Integer,nullable=False)

class WarehouseModel(db.Model):
    __tablename__='GWarehouse' #仓库表
    warehousecode=db.Column(NVARCHAR(50),primary_key=True)
    warehousename=db.Column(NVARCHAR(50),nullable=False)
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)

class InventoryModel(db.Model):
    __tablename__='GInventory' #库存表
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True)
    gmaterial=db.relationship(MaterialModel,backref='stock')
    warehousecode=db.Column(NVARCHAR(50),db.ForeignKey('GWarehouse.warehousecode'),primary_key=True)
    gwarehouse=db.relationship(WarehouseModel,backref='inventory')
    quantity=db.Column(db.Numeric(18,6),nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)

class ReceiptModel(db.Model):
    __tablename__='GReceipt' #收获单表
    receiptid=db.Column(NVARCHAR(50),primary_key=True)
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),nullable=False)
    gmaterial=db.relationship(MaterialModel,backref='receive')
    quantity=db.Column(db.Integer,nullable=False)
    suppliercode=db.Column(NVARCHAR(50),db.ForeignKey('GSupplier.suppliercode'),nullable=False)
    gsupplier=db.relationship(SupplierModel,backref='supply')
    warehousecode=db.Column(NVARCHAR(50),db.ForeignKey('GWarehouse.warehousecode'),nullable=True)
    gwarehouse=db.relationship(WarehouseModel,backref='receipts')
    status=db.Column(NVARCHAR(50),nullable=False)
    pocode=db.Column(NVARCHAR(50),db.ForeignKey('GPOHeader.pocode'),nullable=False)
    gpoheader=db.relationship(POHeaderModel)
    creationtime=db.Column(db.DateTime,nullable=False)
    receiptdate=db.Column(db.DateTime,nullable=True)

class CraftModel(db.Model):
    __tablename__='GCraft' #生产工艺表
    craftid=db.Column(NVARCHAR(50),primary_key=True)
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),nullable=False)
    gmaterial=db.relationship(MaterialModel,backref='craft')
    department=db.Column(NVARCHAR(50),db.ForeignKey('GCharacter.charactercode'),nullable=False)
    gcharacter=db.relationship(CharacterModel,backref='crafts')
    storage=db.Column(NVARCHAR(50),db.ForeignKey('GWarehouse.warehousecode'),nullable=False)
    gwarehouse=db.relationship(WarehouseModel,backref='crafts')
    usagestatus=db.Column(NVARCHAR(10),nullable=False)
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)

class FormulaModel(db.Model):
    __tablename__='GFormula' #工艺配方表
    formulaid=db.Column(NVARCHAR(50),primary_key=True)
    component=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode',name='fk_component_material'),nullable=False)
    gcomponent=db.relationship(MaterialModel,backref='formulas',foreign_keys=[component])
    usage=db.Column(db.Numeric(18,6),nullable=False)
    combination=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode',name='fk_combination_material'),nullable=False)
    gcombination=db.relationship(MaterialModel,backref='combinations',foreign_keys=[combination])
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)
    craftid=db.Column(NVARCHAR(50),db.ForeignKey('GCraft.craftid'),nullable=False)
    gcraft=db.relationship(CraftModel,backref='formulas',foreign_keys=[craftid])




    


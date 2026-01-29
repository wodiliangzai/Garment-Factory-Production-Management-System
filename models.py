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
    fixed=db.Column(NVARCHAR(10),nullable=True)

class PermissionModel(db.Model):
    __tablename__='GPermission' #权限表
    username=db.Column(NVARCHAR(50),db.ForeignKey('GUser.username'),primary_key=True)
    guser=db.relationship(UserModel,backref='permission')
    charactercode=db.Column(NVARCHAR(50),db.ForeignKey('GCharacter.charactercode'),nullable=False)
    gcharacter=db.relationship(CharacterModel)
    keycode=db.Column(db.Integer,nullable=False)

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

class SequenceModel(db.Model):
    __tablename__='GSequence' #工序表
    sequenceid=db.Column(NVARCHAR(50),primary_key=True) #工序编号
    sequencename=db.Column(NVARCHAR(50),nullable=False) #工序名称
    charactercode=db.Column(NVARCHAR(50),db.ForeignKey('GCharacter.charactercode'),nullable=False) #负责角色
    gcharacter=db.relationship(CharacterModel,backref='sequences')
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)

class CraftModel(db.Model):
    __tablename__='GCraft' #生产工艺表
    craftid=db.Column(NVARCHAR(50),primary_key=True)
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),nullable=False)
    gmaterial=db.relationship(MaterialModel,backref='craft')
    sequenceid=db.Column(NVARCHAR(50),db.ForeignKey('GSequence.sequenceid'),nullable=False)
    gsequence=db.relationship(SequenceModel,backref='crafts')
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

class SOHeaderModel(db.Model):
    __tablename__='GSOHeader' #销售订单头
    orderid=db.Column(NVARCHAR(50),primary_key=True) #订单编号
    organization=db.Column(NVARCHAR(50),nullable=False) #客户单位
    clientname=db.Column(NVARCHAR(50),nullable=False) #客户姓名
    clientphone=db.Column(NVARCHAR(20),nullable=False) #客户电话
    address=db.Column(NVARCHAR(50),nullable=False) #客户地址
    remarks=db.Column(NVARCHAR(None),nullable=True) #订单备注
    responsible=db.Column(NVARCHAR(50),nullable=False) #责任人姓名
    creationtime=db.Column(db.DateTime,nullable=False) #创建时间
    creator=db.Column(NVARCHAR(50),nullable=False) #创建人
    orderdate=db.Column(db.DateTime,nullable=False) #下单日期
    deliverydate=db.Column(db.DateTime,nullable=False) #要求交货日期
    orderstatus=db.Column(NVARCHAR(20),nullable=False) #订单状态
    completion=db.Column(db.DateTime,nullable=True) #完成时间

class SOLineModel(db.Model):
    __tablename__='GSOLine' #销售订单行
    orderid=db.Column(NVARCHAR(50),db.ForeignKey('GSOHeader.orderid',ondelete='CASCADE'),primary_key=True) #订单编号
    gsoheader=db.relationship(SOHeaderModel,backref=db.backref('solines', cascade='all, delete-orphan'))
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),primary_key=True) #物料编码
    gmaterial=db.relationship(MaterialModel,backref='solines')
    quantity=db.Column(db.Integer,nullable=False) #数量
    unitprice=db.Column(db.Numeric(18,6),nullable=False) #单价

class TOPModel(db.Model):
    __tablename__='GTOP' #生产任务单表
    taskid=db.Column(NVARCHAR(50),primary_key=True) #任务单编号
    taskcode=db.Column(NVARCHAR(50),nullable=False) #所属任务编码
    taskname=db.Column(NVARCHAR(50),nullable=False) #任务名称
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),nullable=False) #物料编码
    gmaterial=db.relationship(MaterialModel,backref='tasks')
    quantity=db.Column(db.Integer,nullable=False) #生产数量
    taskstatus=db.Column(NVARCHAR(20),nullable=False) #任务状态
    starttime=db.Column(db.DateTime,nullable=True) #开始时间
    finishtime=db.Column(db.DateTime,nullable=False) #计划完成时间
    issuer=db.Column(NVARCHAR(50),db.ForeignKey('GUser.username'),nullable=True) #下达人
    guser=db.relationship(UserModel,backref='tasks')
    creationtime=db.Column(db.DateTime,nullable=False)
    creater=db.Column(NVARCHAR(50), nullable=False)
    altertime=db.Column(db.DateTime, nullable=False)
    alteruser=db.Column(NVARCHAR(50), nullable=False)

class PItemModel(db.Model):
    __tablename__='GPItem' #任务生产项表
    itemid=db.Column(NVARCHAR(50),primary_key=True) #生产项编号
    taskid=db.Column(NVARCHAR(50),db.ForeignKey('GTOP.taskid',ondelete='CASCADE'),nullable=False) #所属任务单
    gtop=db.relationship(TOPModel,backref=db.backref('gpitems', cascade='all, delete-orphan'))
    materialcode=db.Column(NVARCHAR(50),db.ForeignKey('GMaterial.materialcode'),nullable=False) #需产物
    gmaterial=db.relationship(MaterialModel,backref='pitems')
    sequenceid=db.Column(NVARCHAR(50),db.ForeignKey('GSequence.sequenceid'),nullable=False) #所属工序
    gsequence=db.relationship(SequenceModel,backref='pitems')
    quantity=db.Column(db.Numeric(18,6),nullable=False) #需产数量
    craftid=db.Column(NVARCHAR(50),db.ForeignKey('GCraft.craftid'),nullable=False) #关联生产工艺
    gcraft=db.relationship(CraftModel,backref='pitems')
    completed=db.Column(db.Numeric(18,6),nullable=False) #完成数量
    itemqr=db.Column(NVARCHAR(None),nullable=True) #生产项二维码

class PReport(db.Model):
    __tablename__='GPReport' #报产记录表
    reportid=db.Column(NVARCHAR(50),primary_key=True) #报产记录编号
    itemid=db.Column(NVARCHAR(50),db.ForeignKey('GPItem.itemid'),nullable=False) #生产项编号
    gpitem=db.relationship(PItemModel,backref='preports')
    reporter=db.Column(NVARCHAR(50),db.ForeignKey('GPermission.username'),nullable=False) #报产人
    gpermission=db.relationship(PermissionModel,backref='preports')
    reportquantity=db.Column(db.Numeric(18,6),nullable=False) #报产数量
    reporttime=db.Column(db.DateTime,nullable=False) #报产时间
    reviewstatus=db.Column(NVARCHAR(20),nullable=False) #审核状态(待审核/已审核/不通过)
    reviewquantity=db.Column(db.Numeric(18,6),nullable=False) #审核通过数量
    reviewer=db.Column(NVARCHAR(50),db.ForeignKey('GPermission.username'),nullable=True) #审核人
    gpermission_reviewer=db.relationship(PermissionModel,foreign_keys=[reviewer])
    reviewtime=db.Column(db.DateTime,nullable=True) #审核时间
    comments=db.Column(NVARCHAR(None),nullable=True) #审核意见(若已审核则为“通过”，否则写明理由)








    


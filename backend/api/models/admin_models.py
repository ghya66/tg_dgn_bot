"""
Admin 后台管理模型
包括菜单管理、配置管理
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Index, Text, Boolean
from sqlalchemy.sql import func
from src.database import Base


class BotMenu(Base):
    """Bot 菜单配置表"""
    
    __tablename__ = "bot_menus"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    button_text = Column(String(50), nullable=False, comment="按钮文字")
    button_data = Column(String(100), nullable=False, unique=True, comment="按钮数据(callback_data)")
    handler_type = Column(String(20), nullable=False, comment="处理器类型: conversation/command/url")
    handler_name = Column(String(50), comment="处理器名称")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    is_active = Column(Boolean, default=True, comment="是否启用")
    description = Column(String(200), comment="菜单描述")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("idx_active_sort", "is_active", "sort_order"),
        {"comment": "Bot菜单配置表"}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "button_text": self.button_text,
            "button_data": self.button_data,
            "handler_type": self.handler_type,
            "handler_name": self.handler_name,
            "sort_order": self.sort_order,
            "is_active": self.is_active,
            "description": self.description,
        }


class BotSetting(Base):
    """Bot 配置表"""
    
    __tablename__ = "bot_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(100), unique=True, nullable=False, comment="配置键")
    value = Column(Text, nullable=False, comment="配置值")
    value_type = Column(String(20), default="string", comment="值类型: string/int/float/bool/json")
    description = Column(String(200), comment="配置描述")
    category = Column(String(50), default="general", comment="配置分类")
    is_secret = Column(Boolean, default=False, comment="是否敏感信息")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("idx_category", "category"),
        Index("idx_key", "key"),
        {"comment": "Bot配置表"}
    )
    
    def to_dict(self, mask_secret: bool = True):
        """转换为字典"""
        value = self.value
        if mask_secret and self.is_secret:
            value = "***MASKED***"
        
        return {
            "id": self.id,
            "key": self.key,
            "value": value,
            "value_type": self.value_type,
            "description": self.description,
            "category": self.category,
            "is_secret": self.is_secret,
        }


class Product(Base):
    """商品配置表"""
    
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    product_type = Column(String(50), nullable=False, comment="商品类型: premium/energy/trx")
    name = Column(String(100), nullable=False, comment="商品名称")
    description = Column(String(500), comment="商品描述")
    price = Column(String(20), nullable=False, comment="价格(USDT)")
    duration_months = Column(Integer, comment="时长(月) - Premium专用")
    energy_amount = Column(String(50), comment="能量数量 - Energy专用")
    is_active = Column(Boolean, default=True, comment="是否启用")
    sort_order = Column(Integer, default=0, comment="排序顺序")
    
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, onupdate=func.now(), comment="更新时间")
    
    __table_args__ = (
        Index("idx_type_active", "product_type", "is_active"),
        {"comment": "商品配置表"}
    )
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "product_type": self.product_type,
            "name": self.name,
            "description": self.description,
            "price": self.price,
            "duration_months": self.duration_months,
            "energy_amount": self.energy_amount,
            "is_active": self.is_active,
            "sort_order": self.sort_order,
        }

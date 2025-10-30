"""
测试 Admin 数据模型
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.api.models.admin_models import BotMenu, BotSetting, Product
from src.database import Base


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    session = Session(engine)
    yield session
    
    session.close()


class TestBotMenu:
    """测试 BotMenu 模型"""
    
    def test_create_menu(self, db_session):
        """测试创建菜单"""
        menu = BotMenu(
            button_text="测试按钮",
            button_data="test_callback",
            handler_type="conversation",
            handler_name="test_handler",
            sort_order=1,
            is_active=True,
            description="测试菜单"
        )
        
        db_session.add(menu)
        db_session.commit()
        
        assert menu.id is not None
        assert menu.button_text == "测试按钮"
        assert menu.button_data == "test_callback"
    
    def test_menu_to_dict(self, db_session):
        """测试菜单转字典"""
        menu = BotMenu(
            button_text="测试按钮",
            button_data="test_callback",
            handler_type="conversation",
            sort_order=1
        )
        
        db_session.add(menu)
        db_session.commit()
        
        data = menu.to_dict()
        
        assert data["button_text"] == "测试按钮"
        assert data["button_data"] == "test_callback"
        assert data["handler_type"] == "conversation"
        assert data["sort_order"] == 1
    
    def test_menu_unique_button_data(self, db_session):
        """测试按钮数据唯一性"""
        menu1 = BotMenu(
            button_text="按钮1",
            button_data="same_callback",
            handler_type="conversation"
        )
        menu2 = BotMenu(
            button_text="按钮2",
            button_data="same_callback",
            handler_type="conversation"
        )
        
        db_session.add(menu1)
        db_session.commit()
        
        db_session.add(menu2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestBotSetting:
    """测试 BotSetting 模型"""
    
    def test_create_setting(self, db_session):
        """测试创建配置"""
        setting = BotSetting(
            key="test_key",
            value="test_value",
            value_type="string",
            description="测试配置",
            category="test"
        )
        
        db_session.add(setting)
        db_session.commit()
        
        assert setting.id is not None
        assert setting.key == "test_key"
        assert setting.value == "test_value"
    
    def test_setting_to_dict_normal(self, db_session):
        """测试配置转字典（非敏感）"""
        setting = BotSetting(
            key="test_key",
            value="test_value",
            value_type="string",
            is_secret=False
        )
        
        db_session.add(setting)
        db_session.commit()
        
        data = setting.to_dict()
        
        assert data["key"] == "test_key"
        assert data["value"] == "test_value"
    
    def test_setting_to_dict_secret_masked(self, db_session):
        """测试配置转字典（敏感信息遮蔽）"""
        setting = BotSetting(
            key="api_key",
            value="secret-api-key-12345",
            value_type="string",
            is_secret=True
        )
        
        db_session.add(setting)
        db_session.commit()
        
        # 默认遮蔽敏感信息
        data = setting.to_dict(mask_secret=True)
        assert data["value"] == "***MASKED***"
        
        # 不遮蔽敏感信息
        data_unmasked = setting.to_dict(mask_secret=False)
        assert data_unmasked["value"] == "secret-api-key-12345"
    
    def test_setting_unique_key(self, db_session):
        """测试配置键唯一性"""
        setting1 = BotSetting(key="same_key", value="value1", value_type="string")
        setting2 = BotSetting(key="same_key", value="value2", value_type="string")
        
        db_session.add(setting1)
        db_session.commit()
        
        db_session.add(setting2)
        
        with pytest.raises(Exception):  # IntegrityError
            db_session.commit()


class TestProduct:
    """测试 Product 模型"""
    
    def test_create_premium_product(self, db_session):
        """测试创建Premium商品"""
        product = Product(
            product_type="premium",
            name="Premium 3个月",
            description="Telegram Premium会员",
            price="10.0",
            duration_months=3,
            is_active=True,
            sort_order=1
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.id is not None
        assert product.product_type == "premium"
        assert product.duration_months == 3
    
    def test_create_energy_product(self, db_session):
        """测试创建Energy商品"""
        product = Product(
            product_type="energy",
            name="能量闪租",
            description="3 TRX能量",
            price="3.0",
            energy_amount="32000",
            is_active=True
        )
        
        db_session.add(product)
        db_session.commit()
        
        assert product.product_type == "energy"
        assert product.energy_amount == "32000"
    
    def test_product_to_dict(self, db_session):
        """测试商品转字典"""
        product = Product(
            product_type="premium",
            name="Premium 6个月",
            price="18.0",
            duration_months=6
        )
        
        db_session.add(product)
        db_session.commit()
        
        data = product.to_dict()
        
        assert data["product_type"] == "premium"
        assert data["name"] == "Premium 6个月"
        assert data["price"] == "18.0"
        assert data["duration_months"] == 6
    
    def test_query_active_products(self, db_session):
        """测试查询启用的商品"""
        product1 = Product(
            product_type="premium",
            name="Premium 3个月",
            price="10.0",
            is_active=True
        )
        product2 = Product(
            product_type="premium",
            name="Premium 6个月",
            price="18.0",
            is_active=False
        )
        
        db_session.add_all([product1, product2])
        db_session.commit()
        
        active_products = db_session.query(Product).filter_by(is_active=True).all()
        
        assert len(active_products) == 1
        assert active_products[0].name == "Premium 3个月"

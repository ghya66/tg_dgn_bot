"""
测试 Repository 层
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.api.repositories.order_repository import OrderRepository
from backend.api.repositories.user_repository import UserRepository
from backend.api.repositories.setting_repository import SettingRepository
from backend.api.models.admin_models import BotSetting
from src.database import Base, DepositOrder, User


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    session = Session(engine)
    yield session
    
    session.close()


class TestOrderRepository:
    """测试 OrderRepository"""
    
    def test_create_order(self, db_session):
        """测试创建订单"""
        repo = OrderRepository(db_session)
        
        order = repo.create_order(
            user_id=123,
            order_type="premium",
            base_amount=10.0,
            unique_suffix="456",
            total_amount=10.456,
            timeout_minutes=30,
            duration_months=3
        )
        
        assert order.order_id is not None
        assert order.user_id == 123
        assert order.status == "PENDING"
    
    def test_get_by_order_id(self, db_session):
        """测试根据订单ID查询"""
        repo = OrderRepository(db_session)
        
        order = repo.create_order(
            user_id=123,
            order_type="premium",
            base_amount=10.0,
            unique_suffix="456",
            total_amount=10.456
        )
        
        found = repo.get_by_order_id(order.order_id)
        assert found is not None
        assert found.order_id == order.order_id
    
    def test_get_by_suffix(self, db_session):
        """测试根据后缀查询"""
        repo = OrderRepository(db_session)
        
        order = repo.create_order(
            user_id=123,
            order_type="premium",
            base_amount=10.0,
            unique_suffix="789",
            total_amount=10.789
        )
        
        found = repo.get_by_suffix("789")
        assert found is not None
        assert found.unique_suffix == 789
    
    def test_update_status(self, db_session):
        """测试更新订单状态"""
        repo = OrderRepository(db_session)
        
        order = repo.create_order(
            user_id=123,
            order_type="premium",
            base_amount=10.0,
            unique_suffix="456",
            total_amount=10.456
        )
        
        updated = repo.update_status(order.order_id, "PAID")
        assert updated is not None
        assert updated.status == "PAID"
    
    def test_get_user_orders(self, db_session):
        """测试获取用户订单列表"""
        repo = OrderRepository(db_session)
        
        # 创建多个订单
        repo.create_order(123, "premium", 10.0, "001", 10.001)
        repo.create_order(123, "deposit", 20.0, "002", 20.002)
        repo.create_order(456, "premium", 30.0, "003", 30.003)
        
        # 查询用户123的所有订单
        orders = repo.get_user_orders(123)
        assert len(orders) == 2
        
        # Note: 当前 DepositOrder 表没有 order_type 字段，无法按类型过滤
    
    def test_get_pending_orders(self, db_session):
        """测试获取待支付订单"""
        repo = OrderRepository(db_session)
        
        # 创建过期订单
        expired_time = datetime.now() - timedelta(hours=1)
        order = repo.create_order(123, "premium", 10.0, "001", 10.001)
        order.expires_at = expired_time
        db_session.commit()
        
        # 查询过期订单
        pending = repo.get_pending_orders(before=datetime.now())
        assert len(pending) >= 1


class TestUserRepository:
    """测试 UserRepository"""
    
    def test_get_or_create_new_user(self, db_session):
        """测试创建新用户"""
        repo = UserRepository(db_session)
        
        user = repo.get_or_create(user_id=123, username="testuser")
        
        assert user.user_id == 123
        assert user.username == "testuser"
        assert user.get_balance() == 0.0
    
    def test_get_or_create_existing_user(self, db_session):
        """测试获取已存在用户"""
        repo = UserRepository(db_session)
        
        # 第一次创建
        user1 = repo.get_or_create(user_id=123, username="testuser")
        
        # 第二次获取
        user2 = repo.get_or_create(user_id=123, username="testuser")
        
        assert user1.user_id == user2.user_id
    
    def test_update_balance(self, db_session):
        """测试更新余额"""
        repo = UserRepository(db_session)
        
        user = repo.get_or_create(user_id=123)
        
        # 增加余额
        repo.update_balance(123, 100.0)
        
        updated = repo.get_by_user_id(123)
        assert updated.get_balance() == 100.0
    
    def test_debit_balance_success(self, db_session):
        """测试扣除余额（成功）"""
        repo = UserRepository(db_session)
        
        user = repo.get_or_create(user_id=123)
        repo.update_balance(123, 100.0)
        
        # 扣除余额
        repo.debit_balance(123, 30.0)
        
        updated = repo.get_by_user_id(123)
        assert updated.get_balance() == 70.0
    
    def test_debit_balance_insufficient(self, db_session):
        """测试扣除余额（余额不足）"""
        repo = UserRepository(db_session)
        
        user = repo.get_or_create(user_id=123)
        repo.update_balance(123, 10.0)
        
        # 余额不足时抛出异常
        with pytest.raises(ValueError, match="Insufficient balance"):
            repo.debit_balance(123, 20.0)


class TestSettingRepository:
    """测试 SettingRepository"""
    
    def test_get_by_key(self, db_session):
        """测试根据键获取配置"""
        repo = SettingRepository(db_session)
        
        # 创建配置
        repo.create(key="test_key", value="test_value", value_type="string")
        
        setting = repo.get_by_key("test_key")
        assert setting is not None
        assert setting.value == "test_value"
    
    def test_get_value_with_type_conversion(self, db_session):
        """测试获取配置值（类型转换）"""
        repo = SettingRepository(db_session)
        
        # 整数
        repo.create(key="int_key", value="42", value_type="int")
        assert repo.get_value("int_key") == 42
        
        # 浮点数
        repo.create(key="float_key", value="3.14", value_type="float")
        assert repo.get_value("float_key") == 3.14
        
        # 布尔值
        repo.create(key="bool_key", value="true", value_type="bool")
        assert repo.get_value("bool_key") is True
        
        # JSON
        repo.create(key="json_key", value='{"a": 1}', value_type="json")
        assert repo.get_value("json_key") == {"a": 1}
    
    def test_get_value_default(self, db_session):
        """测试获取不存在的配置（返回默认值）"""
        repo = SettingRepository(db_session)
        
        value = repo.get_value("non_exist", default="default_value")
        assert value == "default_value"
    
    def test_set_value_create(self, db_session):
        """测试设置配置（创建）"""
        repo = SettingRepository(db_session)
        
        setting = repo.set_value("new_key", "new_value", value_type="string")
        
        assert setting.key == "new_key"
        assert setting.value == "new_value"
    
    def test_set_value_update(self, db_session):
        """测试设置配置（更新）"""
        repo = SettingRepository(db_session)
        
        # 创建配置
        repo.set_value("update_key", "old_value", value_type="string")
        
        # 更新配置
        repo.set_value("update_key", "new_value", value_type="string")
        
        setting = repo.get_by_key("update_key")
        assert setting.value == "new_value"
    
    def test_get_by_category(self, db_session):
        """测试根据分类获取配置"""
        repo = SettingRepository(db_session)
        
        # 创建不同分类的配置
        repo.create(key="key1", value="val1", category="cat1")
        repo.create(key="key2", value="val2", category="cat1")
        repo.create(key="key3", value="val3", category="cat2")
        
        cat1_settings = repo.get_by_category("cat1")
        assert len(cat1_settings) == 2

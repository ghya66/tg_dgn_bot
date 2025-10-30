"""
配置 Repository
提供系统配置数据访问接口
"""
from typing import Optional, List, Any
import json
from sqlalchemy.orm import Session
from backend.api.repositories.base_repository import BaseRepository
from backend.api.models.admin_models import BotSetting


class SettingRepository(BaseRepository[BotSetting]):
    """配置 Repository"""
    
    def __init__(self, session: Session):
        super().__init__(BotSetting, session)
    
    def get_by_key(self, key: str) -> Optional[BotSetting]:
        """根据配置键获取配置"""
        return self.session.query(self.model).filter_by(key=key).first()
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """获取配置值（自动类型转换）"""
        setting = self.get_by_key(key)
        if not setting:
            return default
        
        return self._convert_value(setting.value, setting.value_type)
    
    def set_value(self, key: str, value: Any, value_type: str = "string", description: str = "") -> BotSetting:
        """设置配置值"""
        setting = self.get_by_key(key)
        
        # 转换值为字符串存储
        str_value = self._to_string(value, value_type)
        
        if setting:
            setting.value = str_value
            setting.value_type = value_type
            if description:
                setting.description = description
            self.session.commit()
            self.session.refresh(setting)
        else:
            setting = self.create(
                key=key,
                value=str_value,
                value_type=value_type,
                description=description
            )
        
        return setting
    
    def get_by_category(self, category: str) -> List[BotSetting]:
        """根据分类获取配置列表"""
        return self.session.query(self.model).filter_by(category=category).all()
    
    def _convert_value(self, value: str, value_type: str) -> Any:
        """转换配置值类型"""
        if value_type == "int":
            return int(value)
        elif value_type == "float":
            return float(value)
        elif value_type == "bool":
            return value.lower() in ("true", "1", "yes")
        elif value_type == "json":
            return json.loads(value)
        else:  # string
            return value
    
    def _to_string(self, value: Any, value_type: str) -> str:
        """转换值为字符串存储"""
        if value_type == "json":
            return json.dumps(value)
        elif value_type == "bool":
            return "true" if value else "false"
        else:
            return str(value)

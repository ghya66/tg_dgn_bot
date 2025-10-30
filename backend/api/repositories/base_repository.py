"""
Repository 基类
提供通用的数据访问方法
"""
from typing import Generic, TypeVar, Type, Optional, List, Any
from sqlalchemy.orm import Session
from sqlalchemy import select

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Repository 基类"""
    
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session
    
    def get_by_id(self, id: int) -> Optional[T]:
        """根据ID获取记录"""
        return self.session.query(self.model).filter_by(id=id).first()
    
    def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """获取所有记录"""
        return self.session.query(self.model).offset(skip).limit(limit).all()
    
    def create(self, **kwargs) -> T:
        """创建记录"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        return instance
    
    def update(self, id: int, **kwargs) -> Optional[T]:
        """更新记录"""
        instance = self.get_by_id(id)
        if not instance:
            return None
        
        for key, value in kwargs.items():
            setattr(instance, key, value)
        
        self.session.commit()
        self.session.refresh(instance)
        return instance
    
    def delete(self, id: int) -> bool:
        """删除记录"""
        instance = self.get_by_id(id)
        if not instance:
            return False
        
        self.session.delete(instance)
        self.session.commit()
        return True
    
    def count(self) -> int:
        """统计记录数"""
        return self.session.query(self.model).count()

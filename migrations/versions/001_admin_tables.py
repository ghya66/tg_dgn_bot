"""Add admin tables and optimize indexes

Revision ID: 001_admin_tables
Revises: 
Create Date: 2025-10-29

说明：
1. 创建 bot_menus 表（菜单配置）
2. 创建 bot_settings 表（系统配置）
3. 创建 products 表（商品配置）
4. 优化现有 deposit_orders 表的索引
5. 优化现有 users 表的索引
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import Index


# revision identifiers
revision = '001_admin_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    """升级数据库"""
    
    # ===== 1. 创建 bot_menus 表 =====
    op.create_table(
        'bot_menus',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('button_text', sa.String(50), nullable=False, comment='按钮文字'),
        sa.Column('button_data', sa.String(100), nullable=False, comment='按钮数据'),
        sa.Column('handler_type', sa.String(20), nullable=False, comment='处理器类型'),
        sa.Column('handler_name', sa.String(50), comment='处理器名称'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序顺序'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('description', sa.String(200), comment='菜单描述'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('button_data'),
        comment='Bot菜单配置表'
    )
    op.create_index('idx_active_sort', 'bot_menus', ['is_active', 'sort_order'])
    
    # ===== 2. 创建 bot_settings 表 =====
    op.create_table(
        'bot_settings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('key', sa.String(100), nullable=False, comment='配置键'),
        sa.Column('value', sa.Text(), nullable=False, comment='配置值'),
        sa.Column('value_type', sa.String(20), default='string', comment='值类型'),
        sa.Column('description', sa.String(200), comment='配置描述'),
        sa.Column('category', sa.String(50), default='general', comment='配置分类'),
        sa.Column('is_secret', sa.Boolean(), default=False, comment='是否敏感信息'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key'),
        comment='Bot配置表'
    )
    op.create_index('idx_category', 'bot_settings', ['category'])
    op.create_index('idx_key', 'bot_settings', ['key'])
    
    # ===== 3. 创建 products 表 =====
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_type', sa.String(50), nullable=False, comment='商品类型'),
        sa.Column('name', sa.String(100), nullable=False, comment='商品名称'),
        sa.Column('description', sa.String(500), comment='商品描述'),
        sa.Column('price', sa.String(20), nullable=False, comment='价格'),
        sa.Column('duration_months', sa.Integer(), comment='时长(月)'),
        sa.Column('energy_amount', sa.String(50), comment='能量数量'),
        sa.Column('is_active', sa.Boolean(), default=True, comment='是否启用'),
        sa.Column('sort_order', sa.Integer(), default=0, comment='排序顺序'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), comment='创建时间'),
        sa.Column('updated_at', sa.DateTime(), comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        comment='商品配置表'
    )
    op.create_index('idx_type_active', 'products', ['product_type', 'is_active'])
    
    # ===== 4. 优化现有表索引 =====
    
    # 检查表是否存在，然后添加索引
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    # deposit_orders 表优化
    if 'deposit_orders' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('deposit_orders')]
        
        if 'idx_user_status' not in existing_indexes:
            op.create_index('idx_user_status', 'deposit_orders', ['user_id', 'status'])
        
        if 'idx_created_at' not in existing_indexes:
            op.create_index('idx_created_at', 'deposit_orders', ['created_at'])
        
        if 'idx_suffix' not in existing_indexes:
            op.create_index('idx_suffix', 'deposit_orders', ['unique_suffix'])
    
    # users 表优化
    if 'users' in inspector.get_table_names():
        existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
        
        if 'idx_user_id' not in existing_indexes:
            op.create_index('idx_user_id', 'users', ['user_id'])
    
    # ===== 5. 插入初始配置数据 =====
    
    # 默认菜单配置
    op.execute("""
        INSERT INTO bot_menus (button_text, button_data, handler_type, handler_name, sort_order, is_active, description)
        VALUES 
            ('🚀 飞机会员', 'premium', 'conversation', 'premium_handler', 1, 1, 'Premium会员直充'),
            ('⚡ TRX兑换', 'trx_exchange', 'conversation', 'trx_exchange_handler', 2, 1, 'USDT兑换TRX'),
            ('🔍 地址监听', 'address_query', 'command', 'address_query_handler', 3, 1, '波场地址查询'),
            ('👤 个人中心', 'profile', 'conversation', 'profile_handler', 4, 1, '个人中心'),
            ('💬 联系客服', 'https://t.me/your_support', 'url', NULL, 5, 1, '联系客服'),
            ('💰 实时U价', 'usdt_price', 'command', 'price_handler', 6, 1, 'USDT实时价格'),
            ('🔄 免费克隆', 'free_clone', 'conversation', 'clone_handler', 7, 1, '免费克隆功能')
    """)
    
    # 默认系统配置
    op.execute("""
        INSERT INTO bot_settings (key, value, value_type, description, category, is_secret)
        VALUES 
            ('order_timeout_minutes', '30', 'int', '订单超时时间(分钟)', 'order', 0),
            ('usdt_trc20_receive_addr', 'TYourReceiveAddress', 'string', 'USDT TRC20收款地址', 'payment', 1),
            ('premium_price_3m', '10.0', 'float', 'Premium 3个月价格', 'premium', 0),
            ('premium_price_6m', '18.0', 'float', 'Premium 6个月价格', 'premium', 0),
            ('premium_price_12m', '30.0', 'float', 'Premium 12个月价格', 'premium', 0),
            ('trx_exchange_rate', '0.15', 'float', 'TRX兑换汇率(USDT/TRX)', 'exchange', 0),
            ('rate_limit_per_minute', '60', 'int', '每分钟请求限制', 'security', 0),
            ('webhook_ip_whitelist', '127.0.0.1,::1', 'string', 'Webhook IP白名单', 'security', 1)
    """)
    
    # 默认商品配置
    op.execute("""
        INSERT INTO products (product_type, name, description, price, duration_months, is_active, sort_order)
        VALUES 
            ('premium', 'Premium 3个月', 'Telegram Premium会员 3个月', '10.0', 3, 1, 1),
            ('premium', 'Premium 6个月', 'Telegram Premium会员 6个月', '18.0', 6, 1, 2),
            ('premium', 'Premium 12个月', 'Telegram Premium会员 12个月', '30.0', 12, 1, 3)
    """)


def downgrade():
    """回滚数据库"""
    
    # 删除优化索引
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if 'deposit_orders' in inspector.get_table_names():
        op.drop_index('idx_suffix', table_name='deposit_orders')
        op.drop_index('idx_created_at', table_name='deposit_orders')
        op.drop_index('idx_user_status', table_name='deposit_orders')
    
    if 'users' in inspector.get_table_names():
        op.drop_index('idx_user_id', table_name='users')
    
    # 删除新表
    op.drop_index('idx_type_active', table_name='products')
    op.drop_table('products')
    
    op.drop_index('idx_key', table_name='bot_settings')
    op.drop_index('idx_category', table_name='bot_settings')
    op.drop_table('bot_settings')
    
    op.drop_index('idx_active_sort', table_name='bot_menus')
    op.drop_table('bot_menus')

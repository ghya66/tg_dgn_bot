# 免费克隆功能说明

## 功能概述

免费克隆功能允许管理员预设服务介绍文案，当用户点击「🎁 免费克隆」按钮时，Bot 会显示这些内容。

## 功能特性

### ✅ 已实现

- 📝 管理员可配置的服务介绍文案

- 🎨 支持 HTML 格式（粗体、换行等）
- 🔘 快捷「联系客服」按钮

- 🔙 返回主菜单按钮
- 🌍 支持环境变量自定义

- ✅ 完整测试覆盖（5个测试用例）

### 📋 默认文案内容

```text
🎁 免费克隆服务

本 Bot 支持免费克隆功能！

📋 服务内容：
• 克隆 Telegram 群组
• 克隆频道内容
• 批量导入成员

💡 申请方式：
需要使用此服务，请联系客服申请。

👨‍💼 客服将为您提供详细的使用指南和技术支持。

```text

## 配置方式

### 方式一：使用默认配置（推荐）

默认文案已在 `src/config.py` 中定义，无需额外配置即可使用。

### 方式二：通过环境变量自定义

在 `.env` 文件中添加：

```bash
FREE_CLONE_MESSAGE="🎁 <b>您的自定义标题</b>\n\n您的自定义内容...\n\n联系客服：@your_support"

```text

## 注意事项：

- 支持 HTML 标签：`<b>`、`<i>`、`<u>`、`<code>` 等
- 使用 `\n` 表示换行

- 最大长度：4096 字符（Telegram 限制）
- 建议包含联系方式或客服信息

## 用户交互流程

```text
主菜单
  ↓
点击「🎁 免费克隆」
  ↓
显示服务介绍文案
  ↓
用户选择：
  ├─ 「👨‍💼 联系客服」→ 跳转到客服页面
  └─ 「🔙 返回主菜单」→ 返回主菜单

```text

## 代码结构

### 配置文件

- **`src/config.py`**: 定义 `free_clone_message` 配置项

- **`.env.example`**: 配置示例和说明

### 处理器

- **`src/menu/main_menu.py`**:

  - `handle_free_clone()`: 处理免费克隆按钮回调

  - 读取配置并显示文案

  - 提供联系客服快捷入口

### 路由注册

- **`src/bot.py`**:

  - 注册 `menu_clone` 回调处理器

  - 绑定到 `MainMenuHandler.handle_free_clone`

### 测试

- **`tests/test_free_clone.py`**: 5 个测试用例

  1. 配置存在性测试

  2. 必要元素检查

  3. 格式验证

  4. 长度限制

  5. 可自定义性

## 管理员使用指南

### 场景 1：使用默认文案

无需任何操作，功能开箱即用。

### 场景 2：修改默认文案

编辑 `src/config.py` 中的 `free_clone_message` 值，修改后重启 Bot。

### 场景 3：动态配置

在 `.env` 文件中设置 `FREE_CLONE_MESSAGE`，无需修改代码。

### 场景 4：多语言支持（未来）

预留扩展：可根据用户语言加载不同文案。

## 技术实现

### 关键代码

**配置定义** (`src/config.py`):

```python
free_clone_message: str = (
    "🎁 <b>免费克隆服务</b>\n\n"
    "本 Bot 支持免费克隆功能！\n\n"
    # ... 更多内容
)

```text

**处理器实现** (`src/menu/main_menu.py`):

```python
@staticmethod
async def handle_free_clone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """处理免费克隆功能"""
    from ..config import settings

    query = update.callback_query
    await query.answer()

    text = settings.free_clone_message

    keyboard = [
        [InlineKeyboardButton("👨‍💼 联系客服", callback_data="menu_support")],
        [InlineKeyboardButton("🔙 返回主菜单", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=reply_markup)

```text

## 测试验证

运行测试：

```bash
pytest tests/test_free_clone.py -v

```text

预期结果：

```text
✅ test_free_clone_message_exists PASSED
✅ test_free_clone_message_contains_required_elements PASSED
✅ test_free_clone_message_format PASSED
✅ test_free_clone_message_length PASSED
✅ test_free_clone_message_customizable PASSED

5 passed in 0.23s

```text

## 未来扩展

### 🔮 可能的增强功能

- 🌍 多语言支持（根据用户语言显示不同文案）

- 📊 统计点击次数
- 🖼️ 支持图片附件

- 📝 富文本编辑器（Web管理后台）
- 🔗 内联按钮自定义（动态添加链接）

- 👥 VIP用户显示不同内容

### 🚫 暂不支持

- ❌ 容器化内容管理（按需求暂不实现）

- ❌ 文件上传/下载
- ❌ 实际克隆操作（仅展示介绍）

## 常见问题

### Q: 如何修改文案？

A: 编辑 `.env` 文件添加 `FREE_CLONE_MESSAGE` 或修改 `src/config.py` 中的默认值。

### Q: 支持哪些 HTML 标签？

A: Telegram 支持的标签：`<b>`、`<i>`、`<u>`、`<s>`、`<code>`、`<pre>`、`<a>`。

### Q: 如何添加链接？

A: 使用 `<a href="https://example.com">链接文字</a>`。

### Q: 文案修改后何时生效？

A: 立即生效（环境变量）或重启 Bot 后生效（代码修改）。

### Q: 可以添加图片吗？

A: 当前版本仅支持文本，图片需要额外开发。

## 总结

✅ **简单易用**：开箱即用，无需复杂配置
✅ **灵活配置**：支持多种自定义方式
✅ **用户友好**：清晰的交互流程
✅ **可扩展**：预留未来增强空间
✅ **测试完备**：5个测试用例保障质量

---

**文档版本**: 1.0
**最后更新**: 2025-10-28
**维护者**: TG DGN Bot Team
